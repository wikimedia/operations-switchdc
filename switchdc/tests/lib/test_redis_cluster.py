import os
import unittest

import redis

from switchdc.tests import base_config_dir, DockerManager
from switchdc.lib.redis_cluster import RedisInstance, RedisShardsBase


class TestRedisBase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # TODO: fix switchdc.remote and switchdc.logger to be more test-friendly
        cls.config_dir = os.path.join(base_config_dir, 'stages.d', 't06_redis')
        cls.config = {}
        cls.docker = DockerManager(base_config_dir, 't06_redis', tag='0.1')
        # Start two redis instances in docker containers and expose them on ports
        # 16379 and 16380 on localhost
        cls.docker.run('t06_redis-1', ports={'6379/tcp': 16379}, detach=True)
        cls.docker.run('t06_redis-2', ports={'6379/tcp': 16380}, detach=True)

    @classmethod
    def tearDownClass(cls):
        cls.docker.cleanup()

    def setUp(self):
        self.red_from = RedisInstance('127.0.0.1', 16379)
        self.red_to = RedisInstance('127.0.0.1', 16380)
        self.red_from.client.slaveof()
        self.red_to.client.slaveof('127.0.0.1', 16379)
        self.red_from.client.set("testkey", "testvalue")


class TestRedisInstance(TestRedisBase):

    def test_init(self):
        inst = RedisInstance('127.0.0.1', 16379, 1, 'password')
        self.assertEqual(inst.host, '127.0.0.1')
        self.assertEqual(inst.db, 1)
        self.assertEqual(inst.password, 'password')
        self.assertIsInstance(inst.client, redis.StrictRedis)

    def test_is_master(self):
        self.assertTrue(self.red_from.is_master)
        self.assertFalse(self.red_to.is_master)

    def test_slave_of(self):
        self.assertIsNone(self.red_from.slave_of)
        self.assertEqual(self.red_to.slave_of, '127.0.0.1:16379')

    def test_stop_replica(self):
        self.red_to.stop_replica()
        self.assertIsNone(self.red_to.slave_of)
        self.assertTrue(self.red_to.is_master)

    def test_start_replica(self):
        self.red_to.stop_replica()
        self.red_from.start_replica(self.red_to)
        self.assertFalse(self.red_from.is_master)
        self.assertEqual(self.red_from.slave_of, str(self.red_to))

    def test_str(self):
        self.assertEqual(str(self.red_from), '127.0.0.1:16379')


class TestRedisShardsBase(TestRedisBase):

    def setUp(self):
        super(TestRedisShardsBase, self).setUp()
        self.rs = RedisShardsBase('sessions', self.config_dir, None)

    def test_init(self):
        self.assertEqual(self.rs.shards['from']['shard1'], self.red_from)
        self.assertEqual(self.rs.shards['from'].keys(), ['shard1'])

    def test_hosts(self):
        self.assertEqual(self.rs.hosts, ['127.0.0.1'])

    def test_datacenters(self):
        self.assertListEqual(sorted(self.rs.datacenters), ['from', 'to'])
