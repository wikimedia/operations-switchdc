from switchdc.lib.remote import Remote
from switchdc.log import logger

__title__ = "Stop puppet execution on maintenance, jobqueues"


def execute(dc_from, dc_to):
    remote = Remote()
    jobrunners = Remote.query('R:class = profile::mediawiki::jobrunner')
    maintenance = Remote.query('R:class = role::mediawiki::maintenance')
    remote.select(jobrunners | maintenance)
    logger.info("Disabling puppet on jobrunners, videoscalers")
    remote.sync('/usr/local/bin/disable-puppet')
