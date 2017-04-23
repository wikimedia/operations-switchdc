import re

from switchdc import ask_confirmation, get_reason
from switchdc.lib.remote import Remote
from switchdc.log import logger

__title__ = 'Switch traffic flow to the appservers from {dc_from} to {dc_to}'


def execute(dc_from, dc_to):
    """Switch traffic from active in dc_from to active in dc_to, cycling through an active-active status."""
    expected_dc_to = r'\+\s+{backend}\.add_backend\(be_{backend}_svc_{dc_to}_wmnet, 100\);'
    expected_dc_from = r'\-\s+{backend}\.add_backend\(be_{backend}_svc_{dc_from}_wmnet, 100\);'

    remote = Remote()
    # Exclude *.wikimedia.org hosts, all production cache hosts are *.$dc.wmnet with the exclusion of
    # cp1008.wikimedia.org which is a special system used for testing.
    dc_query = ('R:class = profile::cumin::target and R:class%site = {site} and R:class%cluster = cache_text and '
                'not *.wikimedia.org')
    to_servers = Remote.query(dc_query.format(site=dc_to))
    from_servers = Remote.query(dc_query.format(site=dc_from))

    remote.select(to_servers)
    logger.info('Running puppet on text caches in {dc_to}'.format(dc_to=dc_to))
    remote.sync('run-puppet-agent --enable "{message}"'.format(message=get_reason()))
    verify_changes(remote.worker, expected_dc_to, dc_from, dc_to)

    logger.info('Text caches traffic is now active-active, running puppet in {dc_from}'.format(dc_from=dc_from))

    remote.select(from_servers)
    remote.sync('run-puppet-agent --enable "{message}"'.format(message=get_reason()))
    verify_changes(remote.worker, expected_dc_from, dc_from, dc_to)

    logger.info('Text caches traffic is now active only in {dc_to}'.format(dc_to=dc_to))


def verify_changes(worker, expected, dc_from, dc_to):
    """Verify that the command output contains the given messages. Fallback to manual confirmation on failure.

    Arguments:
    worker   -- a Cumin's worker to check the results from
    expected -- the expected message pattern, that will be expanded for the list of backends and in which dc_from and
                dc_to will be replaced by their values.
    dc_from  -- the name of the datacenter to switch from
    dc_to    -- the name of the datacenter to switch to
    """
    backends = ('api', 'appservers', 'rendering')
    failed = False

    for nodeset, output in worker.get_results():
        for backend in backends:
            expected_message = expected.format(backend=backend, dc_from=dc_from, dc_to=dc_to)
            if re.search(expected_message, output.message()) is None:
                failed = True
                logger.error("Unable to verify that message '{msg}' is in the output of nodeset '{nodeset}'".format(
                    msg=expected_message, nodeset=nodeset))

    if failed:
        ask_confirmation('Please manually verify that the puppet run was applied with the expected changes')
