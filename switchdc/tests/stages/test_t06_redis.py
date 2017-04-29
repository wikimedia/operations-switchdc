import mock

import switchdc.stages.t06_redis as stage

from switchdc import SwitchdcError
from switchdc.tests.lib.test_redis_cluster import TestRedisBase


class TestRedisShards(TestRedisBase):

    def setUp(self):
        super(TestRedisShards, self).setUp()
        self.rs = stage.RedisShards('sessions', self.config_dir, None)

    def test_stop_replica(self):
        # First test a successful stop
        self.rs.stop_replica('to')
        for inst in self.rs.shards['to'].values():
            self.assertTrue(inst.is_master)
            self.assertIsNone(inst.slave_of)
        # Now let's try to stop the replica again, this should
        # raise no error as all instances should already be masters
        self.rs.stop_replica('to')

    @mock.patch('switchdc.lib.redis_cluster.RedisInstance.stop_replica')
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
        with mock.patch('switchdc.lib.redis_cluster.RedisInstance.stop_replica') as repl:
            repl.side_effect = Exception("I know you hate this")
            self.assertRaises(Exception, self.rs.start_replica, 'from')
        self.rs.stop_replica('from')


class TestStage(TestRedisBase):

    def setUp(self):
        super(TestStage, self).setUp()
        stage.config_dir = self.config_dir
        stage.config = {}

    def test_execute(self):
        stage.execute('from', 'to')
        self.assertTrue(self.red_to.is_master)
        self.assertEqual(self.red_from.slave_of, str(self.red_to))

    def test_execute_redis_fail(self):
        with mock.patch('switchdc.lib.redis_cluster.RedisInstance.stop_replica') as m:
            m.side_effect = ValueError("Bad, sorry")
            with self.assertRaisesRegexp(SwitchdcError, '3'):
                stage.execute('from', 'to')
        # The first cluster has no instances, so no redis call is actually made
        self.assertTrue(self.red_from.is_master)
        self.assertEqual(self.red_to.slave_of, str(self.red_from))
