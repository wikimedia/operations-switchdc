import os

import yaml

from switchdc.log import logger


config_dir = os.environ.get('SWITCHDC_CONFIG_DIR', '/etc/switchdc')


class SwitchdcError(Exception):
    """Custom top Exception class for all custom exceptions."""


def get_global_config():
    """Return the global configuration."""
    return get_config(config_dir)


def get_config(config_path):
    """Parse a YAML config file and return it.

    Arguments:
    config_file -- the path of the configuration file to load
    """
    config_file = os.path.join(config_path, 'config.yaml')
    try:
        with open(config_file, 'r') as fh:
            config = yaml.safe_load(fh)
    except IOError:
        logger.debug("Config file %s not found, using defaults", config_file)
        config = {}
    except Exception as e:
        logger.error("Could not load config file %s: %s", config_file, e)
        config = {}

    return config


def get_reason():
    return 'MediaWiki Switch datacenter'


def ask_confirmation(message):
    print(message)
    print('Type "done" to proceed')

    for _ in xrange(3):
        resp = raw_input('> ')
        if resp == 'done':
            break

        print('Invalid response, please type "done" to proceed. After 3 wrong answers the task will be aborted.')
    else:
        raise SwitchdcError(1)
