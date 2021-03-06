import os
import time

import requests

from switchdc import SwitchdcError
from switchdc.dry_run import is_dry_run
from switchdc.log import logger
from switchdc.lib.confctl import Confctl
from switchdc.lib.remote import Remote, RemoteExecutionError


def check_config_line(filename, expected):
    """Return True if the expected string is found in the configuration file, False otherwise.

    Arguments:
    filename -- filename without extension of wmf-config
    expected -- string expected to be found in the configuration file
    """
    noc_server = Remote.query('R:Class = Role::Noc::Site').pop()
    url = 'http://{noc}/conf/{filename}.php.txt'.format(noc=noc_server, filename=filename)

    try:
        mwconfig = requests.get(url, headers={'Host': 'noc.wikimedia.org'})
    except Exception:
        return False

    found = (expected in mwconfig.text)
    logger.debug('Checked message (found={found}) in MediaWiki config {url}:\n{message}'.format(
        found=found, url=url, message=expected))

    return found


def scap_sync_config_file(filename, message):
    """Execute scap sync-file to deploy a specific configuration file of wmf-config.

    Arguments:
    filename -- filename without extension of wmf-config
    message  -- the message to use for the scap sync-file execution
    """
    logger.debug('Syncing MediaWiki wmf-config/{filename}.php'.format(filename=filename))

    remote = Remote()
    remote.select('R:Class = Deployment::Rsync and R:Class%cron_ensure = absent')
    command = 'su - {user} -c \'scap sync-file --force wmf-config/{filename}.php "{message}"\''.format(
        user=os.getlogin(), filename=filename, message=message)
    remote.sync(command)


def set_readonly(readonly, dc):
    """Set the Conftool readonly variable for MediaWiki config in a specific dc.

    Arguments:
    readonly -- the readonly message to set it read-only, False to set it read-write.
    dc       -- the DC for which the configuration must be changed.
    """
    mwconfig = Confctl('mwconfig')
    mwconfig.update({'val': readonly}, name='ReadOnly', scope=dc)
    for obj in mwconfig.get(scope=dc, name='ReadOnly'):
        if obj.val != readonly and not is_dry_run():
            logger.error('MediaWiki config readonly record was not set: {record}'.format(record=obj.key))
            raise SwitchdcError(1)


def set_master_datacenter(datacenter):
    """Set the MediaWiki config master datacenter variable in Conftool.

    Arguments:
    datacenter -- the new master datacenter.
    """
    mwconfig = Confctl('mwconfig')
    mwconfig.update({'val': datacenter}, name='WMFMasterDatacenter', scope='common')
    for obj in mwconfig.get(name='WMFMasterDatacenter', scope='common'):
        if obj.val != datacenter and not is_dry_run():
            logger.error('MediaWiki config WMFMasterDatacenter record was not set: {record}'.format(
                record=obj.key))
            raise SwitchdcError(1)


def check_siteinfo(jq_query, dc=None, attempts=1, sleep=5):
    """Check that siteinfo JSON matches the jq_query. Raises SwitchdcError on failure.

    Arguments:
    jq_query -- the JQ query to use to determine if the check passes or fails. JQ is run with the -e flag.
    dc       -- filter by the given datacenter, if present. [optional, default: None]
    attempts -- the number of times to retry the check. [optional, default: 1]
    sleep    -- sleep in seconds between attempts. [optional, default: 5]
    """
    logger.debug('Checking MediaWiki siteinfo for {jq_query}'.format(jq_query=jq_query))

    remote = Remote(site=dc)
    remote.select('R:Class = role::mediawiki::webserver')
    command = ("curl -sx localhost:80 -H 'X-Forwarded-Proto: https' "
               "'http://en.wikipedia.org/w/api.php?action=query&meta=siteinfo&format=json&formatversion=2' "
               "| jq -e '{jq_query}'".format(jq_query=jq_query))

    for i in xrange(attempts):
        try:
            logger.debug('Attempt {attempt} checking MediaWiki siteinfo for {jq_query}'.format(
                attempt=i, jq_query=jq_query))
            remote.sync(command, is_safe=True)
            break
        except RemoteExecutionError:
            if i != attempts - 1:
                # Do not sleep after the last attempt
                time.sleep(sleep)
    else:
        logger.error('Reached max attempts ({attempts}) while checking MediaWiki siteinfo for {jq_query}'.format(
            attempts=attempts, jq_query=jq_query))
        raise SwitchdcError(1)


def jobrunners(dc, verify_status, stop=False):
    """Manage and verify the MediaWiki jobrunners.

    Arguments:
    dc            -- the name of the datacenter to filter for.
    verify_status -- the status to verify that the jobrunners are in. Accepted values: 'running', 'stopped'.
    stop          -- whether to stop the jobrunners (True) or left them untouched (False).
    """
    remote = Remote(site=dc)
    remote.select('R:class = role::mediawiki::jobrunner')

    if stop:
        logger.info('Stopping jobrunners in {dc}'.format(dc=dc))
        # We wait for all jobs on HHVM on jobrunners to finish before proceeding
        remote.async('service jobrunner stop', 'service jobchron stop',
                     'while [ "$(hhvmadm /check-load)" -gt 1 ]; do sleep 1; done')

    _validate_status(verify_status)
    if verify_status == 'stopped':
        prefix = '! '
    elif verify_status == 'running':
        prefix = ''

    remote.async('{prefix}service jobrunner status > /dev/null'.format(prefix=prefix),
                 '{prefix}service jobchron status > /dev/null'.format(prefix=prefix), is_safe=True)


def videoscalers(dc, verify_status, stop=False):
    """Manage and verify the MediaWiki videoscalers.

    Arguments:
    dc            -- the name of the datacenter to filter for.
    verify_status -- the status to verify that the videoscalers are in. Accepted values: 'running', 'stopped'.
    stop          -- whether to stop the videoscalers (True) or left them untouched (False).
    """
    remote = Remote(site=dc)
    remote.select('R:class = role::mediawiki::videoscaler')

    if stop:
        logger.info('Stopping videoscalers in {dc}'.format(dc=dc))
        # On videoscalers we are forced to restart HHVM without waiting as transcodes can take a long time
        remote.async('stop jobrunner || exit 0', 'stop jobchron || exit 0', 'restart hhvm')

    _validate_status(verify_status)
    if verify_status == 'stopped':
        option = 'v'
    elif verify_status == 'running':
        option = ''

    remote.async('status jobrunner | grep -q{option} running'.format(option=option),
                 'status jobchron | grep -q{option} running'.format(option=option), is_safe=True)


def cronjobs(dc, verify_status, stop=False):
    """Manage and verify the MediaWiki cronjobs.

    Arguments:
    dc            -- the name of the datacenter to filter for.
    verify_status -- the status to verify that the cronjobs are in. Accepted values: 'running', 'stopped'.
    stop          -- whether to stop the cronjobs (True) or left them untouched (False).
    """
    remote = Remote(site=dc)
    remote.select('R:class = role::mediawiki_maintenance')

    if stop:
        logger.info('Disabling MediaWiki cronjobs in {dc}'.format(dc=dc))
        remote.async('crontab -u www-data -r', 'killall -r php', 'sleep 5', 'killall -9 -r php')

    _validate_status(verify_status)
    if verify_status == 'stopped':
        option = '-z '
    elif verify_status == 'running':
        option = ''

    remote.sync('test {option}"$(crontab -u www-data -l | sed -r \'/^(#|$)/d\')"'.format(option=option), is_safe=True)

    if verify_status == 'stopped':
        # We just log an error, don't actually report a failure to the system. We can live with this.
        try:
            remote.sync('pgrep -c php', is_safe=True)
            logger.error('Stray php processes still present on the maintenance host, please check')
        except RemoteExecutionError:
            pass


def _validate_status(status):
    """Raise SwitchdcError if the status have not a valid value.

    Arguments:
    status -- the status to validate. Accepted values are 'running', 'stopped'.
    """
    valid_statuses = ('running', 'stopped')
    if status not in valid_statuses:
        logger.error("Got invalid status '{status}', expected one of {valid}".format(
            status=status, valid=valid_statuses))
        raise SwitchdcError(1)
