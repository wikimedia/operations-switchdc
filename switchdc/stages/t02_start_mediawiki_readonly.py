from datetime import datetime

from switchdc import SwitchdcError
from switchdc.dry_run import is_dry_run
from switchdc.lib import mediawiki
from switchdc.log import irc_logger, logger

__title__ = "Set MediaWiki in read-only mode (db_from config already merged and git pulled)"


def execute(dc_from, dc_to):
    """Deploy the MediaWiki DB config for dc_from to set MediaWiki in read-only mode.

    Caution: the configuration must have already merged and git pullet in the deployment host.
    """
    message = 'Set MediaWiki in read-only mode in datacenter {dc_from}'.format(dc_from=dc_from)
    filename = 'db-{dc_from}'.format(dc_from=dc_from)
    expected = """'readOnlyBySection' => [
\t's1'      => 'MediaWiki is in read-only mode for maintenance. Please try again in 15 minutes',
\t's2'      => 'MediaWiki is in read-only mode for maintenance. Please try again in 15 minutes',
\t'DEFAULT' => 'MediaWiki is in read-only mode for maintenance. Please try again in 15 minutes', # s3
\t's4'      => 'MediaWiki is in read-only mode for maintenance. Please try again in 15 minutes',
\t's5'      => 'MediaWiki is in read-only mode for maintenance. Please try again in 15 minutes',
\t's6'      => 'MediaWiki is in read-only mode for maintenance. Please try again in 15 minutes',
\t's7'      => 'MediaWiki is in read-only mode for maintenance. Please try again in 15 minutes',
],"""

    if not mediawiki.check_config_line(filename, expected):
        log_message = 'MediaWiki read-only period starts at: {now}'.format(now=datetime.utcnow())
        logger.info(log_message)
        irc_logger.info(log_message)
        mediawiki.scap_sync_config_file(filename, message)
        if not mediawiki.check_config_line(filename, expected) and not is_dry_run():
            logger.error('Read-only mode not changed in the MediaWiki config {filename}?'.format(
                filename=filename))
            raise SwitchdcError(1)
