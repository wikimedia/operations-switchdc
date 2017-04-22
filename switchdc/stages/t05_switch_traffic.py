from switchdc import get_reason, SwitchdcError
from switchdc.lib.remote import Remote
from switchdc.log import logger

__title__ = 'Switch traffic flow to the appservers from {dc_from} to {dc_to}'


def execute(dc_from, dc_to):
    """
    Switch traffic from active in dc_from to active in dc_to,
    cycling through an active-active status
    """
    remote = Remote()
    # Exclude *.wikimedia.org hosts, all production cache hosts are *.$dc.wmnet with the exclusion of
    # cp1008.wikimedia.org which is a special system used for testing.
    dc_query = ('R:class = profile::cumin::target and R:class%site = {site} and R:class%cluster = cache_text and '
                'not *.wikimedia.org')
    to_servers = Remote.query(dc_query.format(site=dc_to))
    from_servers = Remote.query(dc_query.format(site=dc_from))

    remote.select(to_servers)
    logger.info('Running puppet on text caches in {dc}'.format(dc=dc_to))
    remote.sync('run-puppet-agent --enable "{message}"'.format(message=get_reason()))

    print('Please check that the puppet run was applied with the expected changes on all hosts, type "done" to proceed')
    for _ in xrange(3):
        resp = raw_input('> ')
        if resp == 'done':
            break

        print('Invalid response, please type "done" to proceed. After 3 wrong answers the task will be aborted.')
    else:
        raise SwitchdcError(1)

    logger.info('Text caches traffic is now active-active, running puppet in {dc}'.format(dc=dc_from))
    remote.select(from_servers)
    remote.sync('run-puppet-agent --enable "{message}"'.format(message=get_reason()))

    logger.info('Text caches traffic is now active only in {dc}'.format(dc=dc_to))
