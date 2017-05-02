from datetime import datetime

from switchdc.lib import mediawiki
from switchdc.log import irc_logger, logger

__title__ = 'Set MediaWiki in read-only mode in {dc_from}'


def execute(dc_from, dc_to):
    """Set MediaWiki config readonly to True in dc_from and verify it."""
    message = 'MediaWiki is in read-only mode for maintenance. Please try again in a few minutes'
    mediawiki.set_readonly(message, dc=dc_from)

    log_message = 'MediaWiki read-only period starts at: {now}'.format(now=datetime.utcnow())
    logger.info(log_message)
    irc_logger.info(log_message)

    mediawiki.check_siteinfo('.query.general.readonly', attempts=5)
