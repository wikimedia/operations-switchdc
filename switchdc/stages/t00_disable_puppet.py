from switchdc import get_reason
from switchdc.lib.remote import Remote

__title__ = 'Disabling puppet on MediaWiki jobrunners, videoscalers and maintenace systems'


def execute(dc_from, dc_to):
    """Pre-disable puppet on all the hosts where it's needed."""
    remote = Remote()
    # This selects both clusters of mediawiki jobrunners: jobrunner and videoscaler
    jobrunners = Remote.query('R:class = profile::mediawiki::jobrunner')
    maintenance = Remote.query('R:class = role::mediawiki::maintenance')
    remote.select(jobrunners | maintenance)
    remote.sync('disable-puppet "{message}"'.format(message=get_reason()))
