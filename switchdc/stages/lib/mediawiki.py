import os

import requests

from switchdc import remote, SwitchdcError


class MediawikiError(SwitchdcError):
    """Custom exception class for errors of this module."""


def check_config_line(filename, expected):
    """Return True if the expected string is found in the configuration file, False otherwise.

    Arguments:
    filename -- filename without extension of wmf-config
    expected -- string expected to be found in the configuration file
    """
    noc = remote.Remote()
    noc.select('R:Class = Role::Noc::Site')
    noc_server = noc.hosts[0]
    try:
        mwconfig = requests.get('http://{noc}/conf/{filename}.php.txt'.format(noc=noc_server, filename=filename))
    except Exception:
        return False

    return (expected in mwconfig.text)


def scap_sync_config_file(filename, message):
    """Execute scap sync-file to deploy a specific configuration file of wmf-config.

    Arguments:
    filename -- filename without extension of wmf-config
    message  -- the message to use for the scap sync-file execution
    """
    query = 'R:Class = Deployment::Rsync and R:Class%cron_ensure = absent'
    command = 'su - {user} -c \'scap sync-file wmf-config/{filename}.php "{message}"\''.format(
        user=os.getlogin(), filename=filename, message=message)
    rc, _ = remote.run(query, 'sync', [command])
    if rc != 0:
        raise MediawikiError(1)
