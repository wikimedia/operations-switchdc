import os

import requests

from switchdc import SwitchdcError
from switchdc.log import logger
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
