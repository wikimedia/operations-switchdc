import os

import yaml

from switchdc.log import logger


config_dir = os.environ.get('SWITCHDC_CONFIG_DIR', '/etc/switchdc')


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
