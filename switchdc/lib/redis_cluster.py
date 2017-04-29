import os

from collections import defaultdict

import redis
import yaml

from switchdc import SwitchdcError
from switchdc.dry_run import is_dry_run


class RedisSwitchError(SwitchdcError):
    """Custom exception class for Redis errors."""


class RedisInstance(object):

    def __init__(self, ip, port, db=0, password=None):
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


class RedisShardsBase(object):

    def __init__(self, cluster, config_dir, password):
        self.shards = defaultdict(dict)
        with open(os.path.join(config_dir, "{}.yaml".format(cluster))) as fh:
            data = yaml.safe_load(fh)
        self.dry_run = is_dry_run()
        for dc, shards in data.items():
            for shard, redis_data in shards.items():
                self.shards[dc][shard] = RedisInstance(redis_data['host'], redis_data['port'], password=password)

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
