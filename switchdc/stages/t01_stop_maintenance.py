from switchdc.lib import mediawiki

__title__ = 'Stop MediaWiki jobrunners, videoscalers and cronjobs in {dc_from}'


def execute(dc_from, dc_to):
    """Sets mediawiki-maintenance offline, stopping jobrunners, videoscalers and cronjobs."""

    mediawiki.jobrunners(dc_from, 'stopped', stop=True)
    mediawiki.videoscalers(dc_from, 'stopped', stop=True)
    mediawiki.cronjobs(dc_from, 'stopped', stop=True)
