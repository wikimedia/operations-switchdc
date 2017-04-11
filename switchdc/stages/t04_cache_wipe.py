from switchdc.lib import mysql
from switchdc.lib.remote import Remote, RemoteExecutionError
from switchdc.log import logger
from switchdc.stages import get_module_config

__title__ = "wipe and warmup caches"

config = get_module_config('t03_cache_wipe')


def execute(dc_from, dc_to):
    """Wipes out the caches in the inactive datacenter, and then warms them up."""
    mysql.ensure_core_masters_in_sync(dc_from, dc_to)

    logger.info('Wiping out the MediaWiki caches in {dc_to}'.format(dc_to=dc_to))
    to = Remote(site=dc_to)
    to.select('R:class = role::memcached')
    to.sync('service memcached restart')
    to.select('R:class = role::mediawiki::webserver')
    to.sync('service hhvm restart', batch_size=25)

    logger.info('Running the global warmup job in {dc_to}'.format(dc_to=dc_to))
    warmup_dir = config.get('warmup_dir', '/var/lib/mediawiki-cache-warmup')
    base_warmup = "nodejs {wd}/warmup.js {wd}".format(wd=warmup_dir)
    memc_warmup = "{basecmd}/urls-cluster.txt spread appservers.svc.{dc}.wmnet".format(
        dc=dc_to, basecmd=base_warmup)
    appserver_warmup = "{basecmd}/urls-server.txt clone appserver {dc}".format(
        dc=dc_to, basecmd=base_warmup
    )
    api_warmup = "{basecmd}/urls-server.txt clone api_appserver {dc}".format(
        dc=dc_to, basecmd=base_warmup
    )

    remote = Remote()
    remote.select({'wasat.codfw.wmnet'})  # TODO: convert to query once terbium is upgraded
    try:
        remote.sync(memc_warmup, appserver_warmup, api_warmup)
    except RemoteExecutionError as e:
        logger.exception('Cache warmup scripts ended with an error: {}'.format(e.message))
