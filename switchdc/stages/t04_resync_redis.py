import time

from multiprocessing.pool import ThreadPool

import redis

from switchdc.lib.remote import Remote
from switchdc.log import logger
from switchdc.lib.redis_cluster import RedisShardsBase, RedisSwitchError
from switchdc.stages import get_module_config, get_module_config_dir


__title__ = 'Resync the redis for jobqueues in {dc_to} with the masters in {dc_from}'


# TODO: move files to a common config dir?
dirname = 't06_redis'
config = get_module_config(dirname)
config_dir = get_module_config_dir(dirname)
REDIS_PASSWORD = config.get('redis_password', None)

MAX_FAILURES = 3
SLEEP = 2
# Will timeout in less than 5 minutes
MAX_ATTEMPTS = 120


def wait_for_master(instance):
    failures = 0
    attempts = 0
    success = False
    while failures < MAX_FAILURES and attempts < MAX_ATTEMPTS:
        attempts += 1
        try:
            replica = instance.client.info('replication')
        except redis.ConnectionError:
            logger.warning("Failure fetching replication info from {i}".format(i=instance))
            failures += 1
            time.sleep(SLEEP)
            continue

        if replica['role'] != 'slave':
            # Server is a master, raise an error
            logger.error("Instance {i} is a master, cannot wait for its master".format(i=instance))
            break

        if replica['master_link_status'] == 'up' and replica['master_sync_in_progress'] == 0:
            logger.info("Instance {i} has synced with its master".format(i=instance))
            success = True
            break
        else:
            logger.debug(
                'Master link status: {s}, master_sync_in_progress: {p}'.format(
                    s=replica['master_link_status'], p=replica['master_sync_in_progress']))
        time.sleep(SLEEP)

    logger.error("Instance {i} is unreachable or waiting for master timed out".format(i=instance))
    return (instance, success)


class RedisShards(RedisShardsBase):
    MAX_POOL_SIZE = 20

    def check_parallel(self, dc):
        instances = self.shards[dc].values()
        pool = ThreadPool(min(len(instances), self.MAX_POOL_SIZE))
        results = pool.map(wait_for_master, instances)
        return [str(result[0]) for result in results if not result[1]]


def execute(dc_from, dc_to):
    """Resync the Redises for jobqueues before inverting replication"""
    # Restart all redis instances for jobqueues
    logger.info("Restarting all redises for jobqueues in {dc}".format(dc=dc_to))
    remote = Remote(site=dc_to)
    remote.select('R:class = role::jobqueue_redis::master')
    remote.sync('systemctl restart redis-instance-*')

    # Verify
    servers = RedisShards('jobqueue')
    failed = servers.check_parallel(dc_to)
    if failed:
        logger.error("The following instances are still not in sync: {i}".format(', '.join(failed)))
        raise RedisSwitchError(1)
