import os

import requests

from switchdc.dry_run import is_dry_run
from switchdc.log import log_dry_run
from switchdc.lib.remote import Remote


def check_config_line(filename, expected):
    """Return True if the expected string is found in the configuration file, False otherwise.

    Arguments:
    filename -- filename without extension of wmf-config
    expected -- string expected to be found in the configuration file
    """
    noc_server = Remote.query('R:Class = Role::Noc::Site').pop()
    try:
        mwconfig = requests.get('http://{noc}/conf/{filename}.php.txt'.format(noc=noc_server, filename=filename),
                                headers={'Host': 'noc.wikimedia.org'})
    except Exception:
        return False

    found = (expected in mwconfig.text)
    if is_dry_run():
        log_dry_run('Found message in MediaWiki config? {found}. Expected message is:\n{expected}'.format(
            found=found, expected=expected))
        found = True

    return found


def scap_sync_config_file(filename, message):
    """Execute scap sync-file to deploy a specific configuration file of wmf-config.

    Arguments:
    filename -- filename without extension of wmf-config
    message  -- the message to use for the scap sync-file execution
    """
    remote = Remote()
    remote.select('R:Class = Deployment::Rsync and R:Class%cron_ensure = absent')
    command = 'su - {user} -c \'scap sync-file --force wmf-config/{filename}.php "{message}"\''.format(
        user=os.getlogin(), filename=filename, message=message)
    remote.sync(command)
