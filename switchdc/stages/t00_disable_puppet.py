from switchdc.lib.remote import Remote
from switchdc.log import logger

__title__ = "Stop puppet execution on traffic, jobqueues"


def execute(dc_from, dc_to):
    remote = Remote()
    jobrunners = Remote.query('R:class = profile::mediawiki::jobrunner')
    maintenance = Remote.query('R:class = role::mediawiki::maintenance')
    # TODO: maybe just stop in dc_from, dc_to?
    text_caches = Remote.query('R:class = role::cache::text')
    remote.select(jobrunners | maintenance | text_caches)
    logger.info("Disabling puppet on jobrunners, videoscalers and text caches")
    remote.sync('/usr/local/bin/disable-puppet')
