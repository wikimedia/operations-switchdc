import os
import unittest

import mock
import redis

from switchdc import remote
from switchdc.tests import base_config_dir, DockerManager
import switchdc.stages.t05_redis as stage


class TestRedisBase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # TODO: fix switchdc.remote and switchdc.logger to be more test-friendly
        stage.config_dir = os.path.join(base_config_dir, 'stages.d', 't05_redis')
        stage.config = {}
        cls.docker = DockerManager(base_config_dir, 't05_redis', tag='0.1')
        # Start two redis instances in docker containers and expose them on ports
        # 16379 and 16380 on localhost
        cls.docker.run('t05_redis-1', ports={'6379/tcp': 16379}, detach=True)
        cls.docker.run('t05_redis-2', ports={'6379/tcp': 16380}, detach=True)

    @classmethod
    def tearDownClass(cls):
        cls.docker.cleanup()

    def setUp(self):
        self.red_from = stage.RedisInstance('127.0.0.1', 16379)
        self.red_to = stage.RedisInstance('127.0.0.1', 16380)
        self.red_from.client.slaveof()
        self.red_to.client.slaveof('127.0.0.1', 16379)
        self.red_from.client.set("testkey", "testvalue")


class TestRedisInstance(TestRedisBase):

    def test_init(self):
        inst = stage.RedisInstance('127.0.0.1', 16379, 1, 'password')
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


class TestRedisShards(TestRedisBase):

    def setUp(self):
        super(TestRedisShards, self).setUp()
        self.rs = stage.RedisShards('sessions')

    def test_init(self):
        self.assertEqual(self.rs.shards['from']['shard1'], self.red_from)
        self.assertEqual(self.rs.shards['from'].keys(), ['shard1'])

    def test_hosts(self):
        self.assertEqual(self.rs.hosts, ['127.0.0.1'])

    def test_datacenters(self):
        self.assertListEqual(sorted(self.rs.datacenters), ['from', 'to'])

    def test_stop_replica(self):
        # First test a successful stop
        self.rs.stop_replica('to')
        for inst in self.rs.shards['to'].values():
            self.assertTrue(inst.is_master)
            self.assertIsNone(inst.slave_of)
        # Now let's try to stop the replica again, this should
        # raise no error as all instances should already be masters
        self.rs.stop_replica('to')

    @mock.patch('switchdc.stages.t05_redis.RedisInstance.stop_replica')
    def test_stop_replica_failures(self, mock_replica):
        # now let's try to mud the waters and see what happens when errors occur
        mock_replica.side_effect = Exception("I know you hate this")
        self.assertRaises(Exception, self.rs.stop_replica, 'to')

    def test_start_replica(self):
        self.rs.stop_replica('to')
        self.rs.start_replica('from', 'to')
        for shard, inst in self.rs.shards['from'].items():
            self.assertFalse(inst.is_master)
            self.assertEqual(inst.slave_of, str(self.rs.shards['to'][shard]))
        self.rs.stop_replica('from')
        with mock.patch('switchdc.stages.t05_redis.RedisInstance.stop_replica') as repl:
            repl.side_effect = Exception("I know you hate this")
            self.assertRaises(Exception, self.rs.start_replica, 'from')
        self.rs.stop_replica('from')


class TestStage(TestRedisBase):

    @mock.patch('switchdc.remote.execute')
    def test_execute(self, mock_exec):
        mock_exec.return_value = (0, {})
        self.assertEqual(stage.execute('from', 'to'), 0)
        self.assertEqual(mock_exec.call_count, 4)
        self.assertTrue(self.red_to.is_master)
        self.assertEqual(self.red_from.slave_of, str(self.red_to))

    @mock.patch('switchdc.remote.execute')
    def test_execute_cumin_fail(self, mock_exec):
        mock_exec.return_value = (1, mock.MagicMock())
        with self.assertRaises(remote.RemoteExecutionError) as e:
            stage.execute('from', 'to')
        self.assertEqual(e.exception.message, 1)
        self.assertEqual(mock_exec.call_count, 1)
        self.assertTrue(self.red_from.is_master)
        self.assertEqual(self.red_to.slave_of, str(self.red_from))

    @mock.patch('switchdc.remote.execute')
    def test_execute_redis_fail(self, mock_exec):
        mock_exec.return_value = (0, {})
        with mock.patch('switchdc.stages.t05_redis.RedisInstance.stop_replica') as m:
            m.side_effect = ValueError("Bad, sorry")
            self.assertEqual(stage.execute('from', 'to'), 2)
        # The first cluster has no instances, so no redis call is actually made
        self.assertEqual(mock_exec.call_count, 3)
        self.assertTrue(self.red_from.is_master)
        self.assertEqual(self.red_to.slave_of, str(self.red_from))
