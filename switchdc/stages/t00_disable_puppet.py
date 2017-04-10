from switchdc import get_reason
from switchdc.lib.remote import Remote

__title__ = "Stop puppet execution on maintenance, jobqueues"


def execute(dc_from, dc_to):
    remote = Remote()
    jobrunners = Remote.query('R:class = profile::mediawiki::jobrunner')
    maintenance = Remote.query('R:class = role::mediawiki::maintenance')
    remote.select(jobrunners | maintenance)
    remote.sync('disable-puppet "{message}"'.format(message=get_reason(dc_from, dc_to)))
