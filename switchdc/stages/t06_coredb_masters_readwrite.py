from switchdc.log import logger
from switchdc.stages.lib import mysql

__title__ = "set core DB masters in read-write mode"


def execute(dc_from, dc_to):
    """Set all core DB masters (shards: s1-s7, x1, es2-es3) in read-write mode."""
    logger.info('Set all core DB masters (shards: s1-s7, x1, es2-es3) in read-write mode in %s', dc_to)

    try:
        mysql.set_core_masters_readonly(dc_to, False)
        mysql.verify_core_masters_readonly(dc_to, False)
        mysql.verify_core_masters_readonly(dc_from, True)
    except Exception as e:
        logger.error('Unable to set and verify core DB masters are read-write on {dc}: {e}'.format(
            dc=dc_to, e=e.message))
        rc = 1
    else:
        rc = 0

    return rc