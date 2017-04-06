from switchdc import SwitchdcError
from switchdc.lib.remote import Remote
from switchdc.log import logger

__title__ = "Switch traffic flow to the appservers in the new datacenter"


def execute(dc_from, dc_to):
    """
    Switch traffic from active in dc_from to active in dc_to,
    cycling through an active-active status
    """
    remote = Remote()
    dc_query = "R:class = profile::cumin::target and R:class%site = {} and R:class%cluster = cache_text"
    to_servers = Remote.query(dc_query.format(dc_to))
    from_servers = Remote.query(dc_query.format(dc_from))
    remote.select(to_servers | from_servers)
    remote.sync('disable-puppet')
    print 'Please puppet-merge the varnish change, and type "merged"'
    resp = None

    for _ in xrange(3):
        resp = raw_input('> ')
        if resp == "merged":
            break
        else:
            print 'Invalid response, please type "merged"'
    else:
        raise SwitchdcError(1)

    logger.info('Running puppet in {dc}'.format(dc=dc_to))
    remote.select(to_servers)
    remote.sync('run-puppet-agent --force')
    logger.info('Varnish traffic is now active-active')
    logger.info('Running puppet in {dc}'.format(dc=dc_from))
    remote.select(from_servers)
    remote.sync('run-puppet-agent --force')
    logger.info('Varnish traffic is now active only in {dc}'.format(dc=dc_to))
