from switchdc.lib.confctl import Confctl
from switchdc.lib.remote import Remote
from switchdc.log import logger

__title__ = "Start MediaWiki maintenance in the new master DC"


def execute(dc_from, dc_to):
    """Sets mediawiki-maintenance online, starting jobrunners and cronjobs."""
    # 1: This will make any puppet run apply the correct configuration
    discovery = Confctl('discovery')
    discovery.update({'pooled': True}, dnsdisc='mediawiki-maintenance',
                     name=dc_to)

    remote = Remote(site=dc_to)

    # 2: Run puppet on all jobrunner machines
    logger.info('Starting jobrunners in %s', dc_to)
    jobrunners = Remote.query('R:class = role::mediawiki::jobrunner')
    videoscalers = Remote.query('R:class = role::mediawiki::videoscaler')
    all_jobs = videoscalers | jobrunners
    remote.select(all_jobs)
    remote.puppet_run()

    # Verify
    remote.select(jobrunners)
    remote.async('service jobrunner status', 'service jobchron status')

    # 3: Make puppet run on the maintenance host in the new datacenter
    logger.info('Enabling MediaWiki cronjobs in %s', dc_to)
    remote.select('R:class = role::mediawiki::maintenance')
    remote.puppet_run()

    # Verify that the crontab has entries
    remote.sync('test "$(crontab -u www-data -l | sed -r \'^(#|$)/d\')"')
