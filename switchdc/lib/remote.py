from collections import defaultdict

import yaml

from ClusterShell.NodeSet import NodeSet

from cumin.query import QueryBuilder
from cumin.transport import Transport

from switchdc import SwitchdcError
from switchdc.dry_run import is_dry_run
from switchdc.log import logger


# Load cumin's configuration
with open('/etc/cumin/config.yaml', 'r') as f:
    cumin_config = yaml.safe_load(f)


class RemoteExecutionError(SwitchdcError):
    """Custom exception class for errors of this module."""


class Remote(object):

    def __init__(self, site=None):
        if site is None:
            self._site = None
        else:
            self._site = Remote.query('R:Ganglia::Cluster%site = {}'.format(site))
            logger.debug('Filtering host selection for site: {site}'.format(site=site))

        self._hosts = []
        self.worker = None

    @staticmethod
    def query(query_string):
        query = QueryBuilder(query_string, cumin_config, logger).build()
        hosts = set(query.execute())
        logger.debug('Fetched hosts for query: {query}'.format(query=query_string))

        return hosts

    def select(self, q):
        if type(q) is set:
            host_list = q
        else:
            host_list = Remote.query(q)

        if self._site is None:
            self._hosts = list(host_list)
        else:
            self._hosts = list(self._site & host_list)

    def async(self, *commands, **kwargs):
        return self._run('async', commands, **kwargs)

    def sync(self, *commands, **kwargs):
        return self._run('sync', commands, **kwargs)

    def _run(self, mode, commands, success_threshold=1.0, batch_size=None, batch_sleep=0, is_safe=False):
        """Lower level Cumin's execution of commands on a list o hosts.

        Arguments:
        mode              -- the Cumin's mode of execution. Accepted values: sync, async
        commands          -- the list of commands to execute on the matching hosts
        success_threshold -- the threshold to consider the execution still successful. A float between 0.0 and 1.0.
                             [optional, default: 1.0]
        batch_size        -- the batch size to use in cumin. [optional, default: None]
        batch_sleep       -- the batch sleep in seconds to use in Cumin before scheduling the next host.
                             [optional, default: 0]
        is_safe           -- the command is safe to run also in dry-run mode because it's a read-only command that
                             don't change the state. [optional, default: False]
        """
        self.worker = Transport.new(cumin_config, logger)
        self.worker.hosts = self.hosts
        self.worker.commands = list(commands)
        self.worker.handler = mode
        self.worker.success_threshold = success_threshold
        self.worker.batch_size = batch_size
        if batch_sleep > 0:
            self.worker.batch_sleep = batch_sleep

        if is_dry_run():
            logger.debug("Executing commands {commands} on '{num}' hosts: {hosts}".format(
                commands=commands, num=len(self.hosts), hosts=NodeSet.fromlist(self.hosts)))
            if not is_safe:
                return 0

        rc = self.worker.execute()

        if rc != 0 and not is_dry_run():
            raise RemoteExecutionError(rc)

        return 0

    @property
    def hosts(self):
        return self._hosts

    @property
    def failures(self):
        failed_commands = defaultdict(list)
        for node in self.worker._handler_instance.nodes.itervalues():
            if node.state.is_failed:
                failed_commands[node.running_command_index].append(node.name)

        return failed_commands
