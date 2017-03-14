from switchdc.log import logger
from switchdc import remote
from switchdc.stages import get_module_config

__title__ = "wipe and warmup caches"

config = get_module_config('t03_cache_wipe')


def execute(dc_from, dc_to):
    """
    Wipes out the caches in the inactive datacenter, and then warms them up
    """
    logger.info("Wiping out the MediaWiki caches in %s", dc_to)
    rc, _ = remote.run('R:Class = Role::Memcached and *.{}.wmnet'.format(dc_to),
                       'sync', ['service memcached restart'],
                       success_threshold=1.0)
    if rc != 0:
        return rc

    rc, _ = remote.run(
        'R:Class = Role::Mediawiki::Webserver and *.{}.wmnet'.format(dc_to),
        'sync', ['service hhvm restart'], batch_size=25)
    if rc != 0:
        return rc

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
    rc, _ = remote.execute(['wasat.codfw.wmnet'], 'sync',
                           [memc_warmup, appserver_warmup, api_warmup])
    # TODO: log something is rc is != 0 ?
    return 0
