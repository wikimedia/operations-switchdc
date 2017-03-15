import unittest

import mock

from switchdc import remote


class StubNode(object):

    def __init__(self, name, failed):
        self.name = name
        self.state = mock.MagicMock()
        self.state.is_failed = failed
        self.running_command_index = 1


@mock.patch('switchdc.remote.query')
class TestRemote(unittest.TestCase):

    def test_init(self, query_mock):
        r = remote.Remote()
        r._site = None
        query_mock.assert_not_called()
        query_mock.return_value = ['a', 'b', 'c', 'd']
        r = remote.Remote(site='some_site')
        query_mock.assert_called_with('R:ganglia::cluster%site = some_site')
        self.assertEqual(r._site, set(['a', 'b', 'c', 'd']))
        self.assertEqual(r._hosts, [])

    def test_query(self, query_mock):
        query_mock.return_value = []
        q = remote.Remote.query('my_query')
        query_mock.assert_called_with('my_query')
        self.assertEqual(q, set())

    def test_select(self, query_mock):
        site_query_result = ['srv01', 'srv02', 'srv03', 'srv04']
        query_mock.side_effect = [
            site_query_result,
            ['srv02', 'srv03', 'srv06']
        ]
        r = remote.Remote(site='some_site')
        r.select(remote.Remote.query('some_query'))
        self.assertListEqual(['srv02', 'srv03'], r._hosts)
        query_mock.assert_has_calls([
            mock.call('R:ganglia::cluster%site = some_site'),
            mock.call('some_query')])
        query_mock.side_effect = [['srv02', 'ap01']]
        r = remote.Remote()
        r.select(remote.Remote.query('some_query'))
        self.assertListEqual(r._hosts, ['srv02', 'ap01'])

    @mock.patch('switchdc.remote.execute')
    def test_run(self, exec_mock, query_mock):
        site_query_result = ['srv01', 'srv02', 'srv03', 'srv04']
        query_mock.side_effect = [
            site_query_result,
            ['srv02', 'srv03', 'srv06']
        ]
        mock_worker = mock.MagicMock()
        exec_mock.return_value = (0, None)
        r = remote.Remote(site='something')
        r.select(remote.Remote.query('some_query'))
        self.assertEqual(r._run('sync', 'command1', 'command2', some_kwarg="value"), 0)
        exec_mock.assert_called_with(['srv02', 'srv03'], 'sync', ('command1', 'command2'), some_kwarg="value")
        exec_mock.return_value = (1, mock_worker)
        mock_worker._handler_instance.nodes.itervalues.return_value = [
            StubNode('srv02', False),
            StubNode('srv03', True)]
        with self.assertRaises(remote.RemoteExecutionError) as e:
            r._run('sync', 'command1', 'command2')
            self.assertEqual(e.message, 1)
        self.assertEqual(r.failures[1], ['srv03'])
