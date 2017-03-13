import os

import yaml

from switchdc.log import logger

config_dir = os.environ.get('SWITCHDC_CONFIG_DIR', '/etc/switchdc')


def get_module_config_dir(name):
    return os.path.join(config_dir, 'stages.d', name)


def get_module_config(name):
    module_config_file = os.path.join(get_module_config_dir(name), 'config.yaml')
    try:
        with open(module_config_file, 'r') as fh:
            config = yaml.safe_load(fh)
    except IOError:
        logger.debug("Config file %s not found, using defaults",
                     module_config_file)
        config = {}
    except Exception as e:
        logger.error("Could not load config file %s: %s",
                     module_config_file, e)
        config = {}
    return config
