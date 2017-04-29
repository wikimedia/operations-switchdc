import socket

import mock

import switchdc.stages.t04_resync_redis as stage

from switchdc.tests.lib.test_redis_cluster import TestRedisBase


class TestRedisShards(TestRedisBase):
    def setUp(self):
        super(TestRedisShards, self).setUp()
        self.rs = stage.RedisShards('sessions', self.config_dir, None)
        # We need replication to actually work
        self.red_to.client.slaveof(socket.gethostbyname(socket.gethostname()), 16379)

    def test_wait_for_master(self):
        # First of all, check that the destination is a slave and has caught up
        self.assertEqual(stage.wait_for_master(self.red_to), (self.red_to, True))
        # If we do this on the wrong DC, this will fail
        self.assertEqual(stage.wait_for_master(self.red_from), (self.red_from, False))
        # Now let's just kill one of the containers
        self.docker.stop('t06_redis-2')
        self.assertEqual(stage.wait_for_master(self.red_to), (self.red_to, False))

        syncing = {'role': 'slave', 'master_link_status': 'down', 'master_sync_in_progress': 1}
        synced = {'role': 'slave', 'master_link_status': 'up', 'master_sync_in_progress': 0}

        redis_mocker = mock.MagicMock()
        redis_mocker.__str__.return_value = str(self.red_to)
        redis_mocker.client = mock.MagicMock()
        redis_mocker.client.info.side_effect = [syncing, syncing, synced]
        self.assertEqual(stage.wait_for_master(redis_mocker), (redis_mocker, True))
        redis_mocker.client.info.assert_called_with('replication')

    @mock.patch('switchdc.stages.t04_resync_redis.ThreadPool')
    def test_check_parallel(self, mock_pool):
        pool = mock_pool.return_value
        pool.map.return_value = [(self.red_to, False), (self.red_from, True)]
        self.assertEqual([str(self.red_to)], self.rs.check_parallel('to'))
        pool.map.assert_called_with(stage.wait_for_master, [self.red_to])
        mock_pool.assert_called_with(1)
