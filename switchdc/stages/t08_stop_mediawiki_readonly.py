from datetime import datetime

from switchdc.lib import mediawiki
from switchdc.log import irc_logger, logger

__title__ = 'Set MediaWiki in read-write mode in {dc_to}'


def execute(dc_from, dc_to):
    """Set MediaWiki config readonly to False in dc_to and verify it."""
    mediawiki.set_readonly(False, dc=dc_to)

    mediawiki.check_siteinfo('.query.general.readonly | not', dc=dc_to, attempts=5)

    log_message = 'MediaWiki read-only period ends at: {now}'.format(now=datetime.utcnow())
    logger.info(log_message)
    irc_logger.info(log_message)

    mediawiki.check_siteinfo('.query.general.readonly', dc=dc_from, attempts=5)
