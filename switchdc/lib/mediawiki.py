import os

import requests

from switchdc.log import logger
from switchdc.lib.remote import Remote


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
