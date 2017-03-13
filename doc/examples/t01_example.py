from switchdc import remote
from switchdc.log import logger


__title__ = "Example task description"


def execute(dc_from, dc_to):
    """Entry point to execute this task

    Must not raise execeptions, all exceptions must be catched here and managed.
    Returns 0 on success, a positive integer on failure.

    Arguments:
    dc_from -- the name of the datacenter to switch from
    dc_to   -- the name of the datacenter to switch to
    """
    logger.debug(__name__)
    print('Executed with {dc_from} - {dc_to}'.format(dc_from=dc_from, dc_to=dc_to))
    rc, worker = remote.run('R:Class = Role::Memcached', 'sync', ['date'],
                            success_threshold=0.9, batch_size=5, batch_sleep=5)

    return rc
