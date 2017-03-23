import unittest

import mock

from switchdc.lib.remote import Remote, RemoteExecutionError


class StubNode(object):

    def __init__(self, name, failed):
        self.name = name
        self.state = mock.MagicMock()
        self.state.is_failed = failed
        self.running_command_index = 1


@mock.patch('switchdc.lib.remote.Remote.query')
class TestRemote(unittest.TestCase):

    def test_init(self, query_mock):
        r = Remote()
        r._site = None
        query_mock.assert_not_called()
        query_mock.return_value = {'a', 'b', 'c', 'd'}
        r = Remote(site='some_site')
        query_mock.assert_called_with('R:Ganglia::Cluster%site = some_site')
        self.assertEqual(r._site, {'a', 'b', 'c', 'd'})
        self.assertEqual(r.hosts, [])

    def test_query(self, query_mock):
        Remote.query('my_query')
        query_mock.assert_called_with('my_query')

    def test_select(self, query_mock):
        query_mock.return_value = {'srv01', 'srv02', 'srv03', 'srv04'}
        r = Remote(site='some_site')
        query_mock.return_value = {'srv02', 'srv03', 'srv06'}
        r.select(Remote.query('some_query'))
        self.assertListEqual(sorted(['srv02', 'srv03']), sorted(r.hosts))
        query_mock.assert_has_calls([
            mock.call('R:Ganglia::Cluster%site = some_site'),
            mock.call('some_query')])
        query_mock.return_value = {'srv02', 'ap01'}
        r = Remote()
        r.select(Remote.query('some_query'))
        self.assertListEqual(sorted(r.hosts), sorted(['srv02', 'ap01']))

    @mock.patch('switchdc.lib.remote.Remote.sync')
    def test_run(self, exec_mock, query_mock):
        query_mock.return_value = {'srv01', 'srv02', 'srv03', 'srv04'}
        exec_mock.return_value = 0
        r = Remote(site='something')
        query_mock.return_value = {'srv02', 'srv03', 'srv06'}
        r.select(Remote.query('some_query'))
        self.assertEqual(r.sync('command1', 'command2', some_kwarg='value'), 0)
        exec_mock.side_effect = RemoteExecutionError(1)
        worker_mock = mock.Mock()
        worker_mock._handler_instance.nodes.itervalues.return_value = [
            StubNode('srv02', False),
            StubNode('srv03', True)]
        r.worker = worker_mock
        with self.assertRaises(RemoteExecutionError) as e:
            r.sync('command1', 'command2')
            self.assertEqual(e.message, 1)
        self.assertEqual(r.failures[1], ['srv03'])
