import os

from switchdc import config_dir, get_config_file


def get_module_config_dir(name):
    """Return the path of the directory that holds the configuration for a specific module.

    Arguments:
    name -- the name of the module
    """
    return os.path.join(config_dir, 'stages.d', name)


def get_module_config(name):
    """Return the configuration for a specific module.

    Arguments:
    name -- the name of the module
    """
    return get_config_file(get_module_config_dir(name))
