from switchdc import remote
from switchdc.log import logger
from switchdc.stages import get_module_config
from switchdc.stages.lib import mysql

__title__ = "wipe and warmup caches"

config = get_module_config('t03_cache_wipe')


def execute(dc_from, dc_to):
    """
    Wipes out the caches in the inactive datacenter, and then warms them up
    """
    logger.info("Waiting for the masters in %s to catch up", dc_to)
    mysql.ensure_core_masters_in_sync(dc_from)

    logger.info("Wiping out the MediaWiki caches in %s", dc_to)
    to = remote.Remote(site=dc_to)
    to.select('R:class = role::memcached')
    to.sync('service memcached restart')
    to.select('R:class = role::mediawiki::webserver')
    to.sync('service hhvm restart', batch_size=25)

    logger.info("Now running the global warmup job")
    warmup_dir = config.get('warmup_dir', '/var/lib/mediawiki-cache-warmup')
    base_warmup = "nodejs {wd}/warmup.js {wd}".format(wd=warmup_dir)
    memc_warmup = "{basecmd}/urls-cluster.txt spread appservers.svc.{dc}.wmnet".format(
        dc=dc_to, basecmd=base_warmup)
    appserver_warmup = "{basecmd}urls-server.txt clone {dc} appserver".format(
        dc=dc_to, basecmd=base_warmup
    )
    api_warmup = "{basecmd}urls-server.txt clone {dc} api_appserver".format(
        dc=dc_to, basecmd=base_warmup
    )
    # Note: this cannot run on terbium because it's still trusty
    try:
        remote.execute(['wasat.codfw.wmnet'], 'sync', [memc_warmup, appserver_warmup, api_warmup])
    except remote.RemoteExecutionError as e:
        logger.warn('Cache warmup scripts ended with return status %s', e.message)
    return 0
