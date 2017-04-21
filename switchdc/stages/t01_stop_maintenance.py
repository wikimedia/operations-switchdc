from switchdc.lib.remote import Remote, RemoteExecutionError
from switchdc.log import logger

__title__ = "Stop MediaWiki maintenance in the old master DC"


def execute(dc_from, dc_to):
    """Sets mediawiki-maintenance offline, stopping jobrunners and cronjobs."""
    # Note: the two steps here could be run in parallel; split the file here if
    # deemed necessary. Since this is pre-read-only, I didn't think it would be
    # an issue

    # 1: Stop the jobrunners in dc_from
    remote = Remote(site=dc_from)
    logger.info('Stopping jobrunners in {dc}'.format(dc=dc_from))
    remote.select('R:class = role::mediawiki::jobrunner')
    # We wait for all jobs on HHVM on jobrunners to finish before proceeding
    remote.async('service jobrunner stop', 'service jobchron stop',
                 'while [ "$(hhvmadm /check-load)" -gt 1 ]; do sleep 1; done')
    remote.async('! service jobrunner status > /dev/null', '! service jobchron status > /dev/null',  is_safe=True)

    remote.select('R:class = role::mediawiki::videoscaler')
    # On videoscalers we are forced to restart HHVM as transcodes can take a long time
    remote.async('stop jobrunner || exit 0', 'stop jobchron || exit 0', 'restart hhvm')
    remote.async('status jobrunner | grep -qv running', 'status jobchron | grep -qv running')

    # 2: disable and kill cronjobs
    logger.info('Disabling MediaWiki cronjobs in {dc}'.format(dc=dc_from))
    remote.select('R:class = role::mediawiki::maintenance')
    remote.async('crontab -u www-data -r', 'killall -r php', 'sleep 5', 'killall -9 -r php')

    # Verify that the crontab has no entries
    remote.sync('test -z "$(crontab -u www-data -l | sed -r  \'/^(#|$)/d\')"', is_safe=True)

    # We just log an error, don't actually report a failure to the system. We can live with this.
    try:
        remote.sync('pgrep -c php', is_safe=True)
        logger.error('Stray php processes still present on the maintenance host, please check')
    except RemoteExecutionError:
        pass
