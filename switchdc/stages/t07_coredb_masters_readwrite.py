from switchdc import SwitchdcError
from switchdc.lib import mysql
from switchdc.log import logger

__title__ = 'Set core DB masters in read-write mode in {dc_to}, ensure masters in {dc_from} are read-only'


def execute(dc_from, dc_to):
    """Set all core DB masters (shards: s1-s7, x1, es2-es3) in read-write mode."""
    try:
        mysql.set_core_masters_readonly(dc_to, False)
        mysql.verify_core_masters_readonly(dc_to, False)
        mysql.verify_core_masters_readonly(dc_from, True)
    except SwitchdcError:
        raise
    except Exception as e:
        logger.error('Unable to set and verify core DB masters are read-write on {dc}: {e}'.format(
            dc=dc_to, e=e.message))
        raise SwitchdcError(1)
