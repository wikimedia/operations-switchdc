from switchdc import get_reason
from switchdc.lib.remote import Remote

__title__ = 'Start MediaWiki jobrunners, videoscalers and maintenance in {dc_to}'


def execute(dc_from, dc_to):
    """Sets mediawiki-maintenance online, starting jobrunners and cronjobs."""
    remote = Remote(site=dc_to)

    # 1: Run puppet on all jobrunner and maintenace machines in dc_to
    jobrunners = Remote.query('R:class = role::mediawiki::jobrunner')
    videoscalers = Remote.query('R:class = role::mediawiki::videoscaler')
    maintenance = Remote.query('R:class = role::mediawiki::maintenance')
    all_jobs = videoscalers | jobrunners | maintenance
    remote.select(all_jobs)
    command = 'run-puppet-agent --enable "{message}"'.format(message=get_reason())
    remote.async(command, batch_size=30)

    # Verify
    remote.select(jobrunners)
    remote.async('service jobrunner status > /dev/null', 'service jobchron status > /dev/null', is_safe=True)

    remote.select(videoscalers)
    remote.async('status jobrunner | grep -q running', 'status jobchron | grep -q running')
    # Verify that the crontab has entries
    remote.select(maintenance)
    remote.sync('test "$(crontab -u www-data -l | sed -r \'/^(#|$)/d\')"', is_safe=True)
