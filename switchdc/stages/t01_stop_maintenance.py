from switchdc import SwitchdcError
from switchdc.lib import puppet
from switchdc.lib.confctl import Confctl
from switchdc.lib.remote import Remote, RemoteExecutionError
from switchdc.log import logger

__title__ = "Stop MediaWiki maintenance in the old master DC"


def execute(dc_from, dc_to):
    """Sets mediawiki-maintenance offline, stopping jobrunners and cronjobs."""
    # This will make any puppet run apply the correct configuration
    discovery = Confctl('discovery')
    discovery.update({'pooled': False}, dnsdisc='mediawiki-maintenance',
                     name=dc_from)
    for obj in discovery.get(dnsdisc='mediawiki-maintenance', name=dc_from):
        if obj.pooled:
            logger.error("Discovery object %s should be depooled", obj.tags)
            raise SwitchdcError(1)

    # 2: Stop the jobrunners in dc_from
    remote = Remote(site=dc_from)
    logger.info('Stopping jobrunners in %s', dc_from)
    jobrunners = Remote.query('R:class = role::mediawiki::jobrunner')
    videoscalers = Remote.query('R:class = role::mediawiki::videoscaler')
    all_jobs = videoscalers | jobrunners
    remote.select(all_jobs)

    remote.async('service jobrunner stop', 'service jobchron stop', 'service hhvm restart')

    # verify
    remote.select(jobrunners)
    remote.async('! service jobrunner status', '! service jobchron status')

    # 3: disable and kill cronjobs
    logger.info('Disabling MediaWiki cronjobs in %s', dc_from)
    remote.select('R:class = role::mediawiki::maintenance')
    remote.async(
        puppet.get_agent_run_command(), 'killall php', 'killall php5', 'sleep 5',
        'killall -9 php', 'killall -9 php5')

    # Verify that the crontab has no entries
    remote.sync('test -z "$(crontab -u www-data -l | sed -r  \'/^(#|$)/d\')"')

    # We just log an error, don't actually report a failure to the system. We can live with this.
    try:
        remote.sync('pgrep php')
        logger.error('Stray php processes still present on the maintenance host, please check')
    except RemoteExecutionError:
        pass
