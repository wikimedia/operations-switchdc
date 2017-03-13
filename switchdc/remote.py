import yaml

from cumin.query import QueryBuilder
from cumin.transport import Transport

from switchdc.log import logger


# Load cumin's configuration
with open('/etc/cumin/config.yaml', 'r') as f:
    cumin_config = yaml.safe_load(f)


def run(query_string, mode, commands, success_threshold=1.0, batch_size=None, batch_sleep=0):
    """High level Cumin run of commands on hosts matching the query.

    Arguments:
    query_string      -- the hosts selection query to use with Cumin's configured backend
    mode              -- the Cumin's mode of execution. Accepted values: sync, async
    commands          -- the list of commands to execute on the matching hosts
    success_threshold -- the threshold to consider the execution still successful. A float between 0.0 and 1.0.
                         [optional, default: 1.0]
    batch_size        -- the batch size to use in cumin. [optional, default: None]
    batch_sleep       -- the batch sleep in seconds to use in Cumin before scheduling the next host.
                         [optional, default: 0]
    """
    hosts = query(query_string)
    return execute(hosts, mode, commands, success_threshold, batch_size, batch_sleep)


def query(query_string):
    """Lower level Cumin's backend query to find matching hosts. Use run() when possible.

    Arguments:
    query_string -- the hosts selection query to use with Cumin's configured backend
    """
    query = QueryBuilder(query_string, cumin_config, logger).build()
    return query.execute()


def execute(hosts, mode, commands, success_threshold=1.0, batch_size=None, batch_sleep=0):
    """Lower level Cumin's execution of commands on a list o hosts. Use run() when possible.

    Arguments:
    hosts             -- the list of matching hosts to use as a target for Cumin's transport
    mode              -- the Cumin's mode of execution. Accepted values: sync, async
    commands          -- the list of commands to execute on the matching hosts
    success_threshold -- the threshold to consider the execution still successful. A float between 0.0 and 1.0.
                         [optional, default: 1.0]
    batch_size        -- the batch size to use in cumin. [optional, default: None]
    batch_sleep       -- the batch sleep in seconds to use in Cumin before scheduling the next host.
                         [optional, default: 0]
    """
    worker = Transport.new(cumin_config, logger)
    worker.hosts = hosts
    worker.commands = commands
    worker.handler = mode
    worker.success_threshold = success_threshold
    worker.batch_size = batch_size
    worker.batch_sleep = batch_sleep

    rc = worker.execute()

    return rc, worker


def get_puppet_agent_command(noop=False):
    """Return puppet agent command equivalent to --test without --detailed-exitcodes."""
    command = 'puppet agent -ov --ignorecache --no-daemonize --no-usecacheonfailure --no-splay --show_diff'
    if noop:
        command += ' --noop'

    return command
