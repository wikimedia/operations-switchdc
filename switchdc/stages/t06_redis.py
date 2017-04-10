from collections import defaultdict

import redis
import yaml

from switchdc import SwitchdcError
from switchdc.dry_run import is_dry_run
from switchdc.log import logger
from switchdc.stages import get_module_config, get_module_config_dir

__title__ = 'Switch the Redis replication'

dirname = __name__.split('.')[-1]
config = get_module_config(dirname)
config_dir = get_module_config_dir(dirname)

REDIS_PASSWORD = config.get('redis_password', None)


class RedisSwitchError(SwitchdcError):
    """Custom exception class for Redis errors."""


class RedisInstance(object):

    def __init__(self, ip, port, db=0, password=REDIS_PASSWORD):
        self.host = ip
        self.port = port
        self.db = db
        self.password = password
        # The client will be lazily initialized once we need it
        self.client = redis.StrictRedis(self.host, self.port, self.db, self.password)

    @property
    def is_master(self):
        return (self.client.info('replication')['role'] == 'master')

    @property
    def slave_of(self):
        data = self.client.info('replication')
        try:
            return '{}:{}'.format(data['master_host'], data['master_port'])
        except:
            return None

    def stop_replica(self):
        self.client.slaveof()

    def start_replica(self, master):
        self.client.slaveof(master.host, master.port)

    def __str__(self):
        return "{}:{}".format(self.host, self.port)

    def __eq__(self, other):
        return (self.host == other.host and
                self.port == other.port and
                self.db == other.db and
                self.password == other.password)

    def __ne__(self, other):
        return not self.__eq__(other)


class RedisShards(object):

    def __init__(self, cluster):
        self.shards = defaultdict(dict)
        with open('{}/{}.yaml'.format(
                config_dir, cluster)) as fh:
            data = yaml.safe_load(fh)
        self.dry_run = is_dry_run()
        for dc, shards in data.items():
            for shard, redis_data in shards.items():
                self.shards[dc][shard] = RedisInstance(redis_data['host'],
                                                       redis_data['port'])

    @property
    def hosts(self):
        hosts = set()
        for shards in self.shards.values():
            for instance in shards.values():
                hosts.add(instance.host)
        return list(hosts)

    @property
    def datacenters(self):
        return self.shards.keys()

    def stop_replica(self, dc):
        for instance in self.shards[dc].values():
            if instance.is_master:
                logger.warning("Instance %s is already master, doing nothing", instance)
                continue
            try:
                logger.debug("Stopping replica on {instance}".format(instance=instance))
                if not self.dry_run:
                    instance.stop_replica()
            except Exception as e:
                logger.error("Generic failure while stopping replica on %s: %s", instance, e)
                raise

            if not instance.is_master and not self.dry_run:
                logger.error("Instance %s is still a slave of %s, aborting",
                             instance, instance.slave_of)
                raise RedisSwitchError(1)

    def start_replica(self, dc, dc_master):
        for shard, instance in self.shards[dc].items():
            master = self.shards[dc_master][shard]
            if instance.slave_of == str(master):
                logger.debug('Replica already configured on {instance}'.format(instance=instance))
            else:
                logger.debug('Starting replica {master} => {local}'.format(master=master, local=instance))
                if not self.dry_run:
                    instance.start_replica(master)

            if instance.slave_of != str(master) and not self.dry_run:
                logger.error("Replica on %s is not correctly configured", instance)
                raise RedisSwitchError(2)


def execute(dc_from, dc_to):
    """Switches the replication for both redis clusters for mediawiki (jobqueue and sessions)."""
    for cluster in ('jobqueue', 'sessions'):
        try:
            servers = RedisShards(cluster)
        except Exception, e:
            logger.error("Failed loading redis data: %s", e, exc_info=True)
            raise SwitchdcError(1)

        # Now let's disable replication
        logger.info("Stopping replication for all instances in %s, cluster %s", dc_to, cluster)
        try:
            servers.stop_replica(dc_to)
        except RedisSwitchError:
            raise
        except Exception as e:
            logger.error('Failed to stop replication for all instances in %s, cluster %s: %s',
                         dc_to, cluster, e.message)
            raise SwitchdcError(3)

        logger.info("Starting replication for all instances in %s, cluster %s",
                    dc_from, cluster)
        try:
            servers.start_replica(dc_from, dc_to)
        except RedisSwitchError:
            raise
        except Exception:
            logger.error('Failed to start replication for all instances in %s, cluster %s',
                         dc_to, cluster, e.message)
            raise SwitchdcError(4)
