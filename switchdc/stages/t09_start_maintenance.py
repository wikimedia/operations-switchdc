from switchdc import get_reason
from switchdc.lib import mediawiki
from switchdc.lib.remote import Remote

__title__ = 'Start MediaWiki jobrunners, videoscalers and maintenance in {dc_to}'


def execute(dc_from, dc_to):
    """Sets mediawiki-maintenance online, starting jobrunners, videoscalers and cronjobs."""
    # Enable and run puppet on the hosts where it was disabled
    remote = Remote()
    remote.select('R:class = profile::mediawiki::jobrunner or R:class = role::mediawiki::maintenance')
    command = 'run-puppet-agent --enable "{message}"'.format(message=get_reason())
    remote.async(command, batch_size=30)

    # Verify all services are started in dc_to
    mediawiki.jobrunners(dc_to, 'running')
    mediawiki.videoscalers(dc_to, 'running')
    mediawiki.cronjobs(dc_to, 'running')

    # Verify all services are still stopped in dc_from
    mediawiki.jobrunners(dc_from, 'stopped')
    mediawiki.videoscalers(dc_from, 'stopped')
    mediawiki.cronjobs(dc_from, 'stopped')
