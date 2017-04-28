from switchdc import get_reason
from switchdc.lib.remote import Remote
from switchdc.log import logger

__title__ = 'Disabling puppet on selected hosts in {dc_from} and {dc_to}'


def execute(dc_from, dc_to):
    """Pre-disable puppet on all the hosts where it's needed."""
    remote = Remote()
    # This selects both clusters of mediawiki jobrunners: jobrunner and videoscaler
    jobrunners = Remote.query('R:class = profile::mediawiki::jobrunner')
    maintenance = Remote.query('R:class = role::mediawiki_maintenance')
    remote.select(jobrunners | maintenance)
    logger.info('Disabling puppet on MediaWiki jobrunners, videoscalers and maintenance hosts')
    remote.sync('disable-puppet "{message}"'.format(message=get_reason()))

    # Disable puppet in cache text in both DCs
    logger.info('Disabling puppet on text caches in {dc_from}, {dc_to}'.format(dc_from=dc_from, dc_to=dc_to))
    # Exclude *.wikimedia.org hosts, all production cache hosts are *.$dc.wmnet with the exclusion of
    # cp1008.wikimedia.org which is a special system used for testing.
    dc_query = ('R:class = profile::cumin::target and R:class%site = {site} and R:class%cluster = cache_text and '
                'not *.wikimedia.org')
    to_servers = Remote.query(dc_query.format(site=dc_to))
    from_servers = Remote.query(dc_query.format(site=dc_from))
    remote.select(to_servers | from_servers)
    remote.sync('disable-puppet "{message}"'.format(message=get_reason()))

    logger.info('The puppet change for text caches MUST be merged before running the switch traffic task')
