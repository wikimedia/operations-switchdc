from switchdc import remote
from switchdc.log import logger
from switchdc.stages import get_module_config

__title__ = "Example task description"

# Standard location for config files specific to this module:
# ${CONFIG_DIR}/stages.d/t01_example
conf = get_module_config(__name__)
# Tests should go in switchdc/tests/test_t01_example.py and fixture files in
# switchdc/tests/fixtures/stages.d/t01_example


def execute(dc_from, dc_to):
    """Entry point to execute this task

    All exceptions not raised by cumin should be managed.
    Returns 0 on success, a positive integer on failure.

    Arguments:
    dc_from -- the name of the datacenter to switch from
    dc_to   -- the name of the datacenter to switch to
    """
    logger.debug(__name__)
    print('Executed with {dc_from} - {dc_to}'.format(dc_from=dc_from, dc_to=dc_to))
    # Act on the nodes in dc_to
    to = remote.Remote(site=dc_to)
    # Select a class of hosts
    to.select('R:Class = Role::Memcached')
    # Execute the commands listed in async mode
    # This could raise an exception that is handled in the master script
    to.async('date', 'ls -la /tmp',
             success_threshold=0.9, batch_size=5, batch_sleep=5)

    return 0
