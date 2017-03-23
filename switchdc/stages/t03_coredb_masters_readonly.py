from switchdc.lib import mysql
from switchdc.log import logger

__title__ = "set core DB masters in read-only mode"


def execute(dc_from, dc_to):
    """Set all core DB masters (shards: s1-s7, x1, es2-es3) in read-only mode."""
    logger.info('Set all core DB masters (shards: s1-s7, x1, es2-es3) in read-only mode in %s', dc_from)

    try:
        mysql.set_core_masters_readonly(dc_from, True)
        mysql.verify_core_masters_readonly(dc_from, True)
        mysql.verify_core_masters_readonly(dc_to, True)
    except Exception as e:
        logger.error('Unable to set and verify core DB masters are read-only on {dc}: {e}'.format(
            dc=dc_to, e=e.message))
        rc = 1
    else:
        rc = 0

    return rc
