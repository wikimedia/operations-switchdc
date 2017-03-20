from switchdc import conftool
from switchdc.log import logger
from switchdc.stages.lib import mediawiki

__title__ = "Switch MediaWiki configuration to the new datacenter"


def execute(dc_from, dc_to):
    """
    Switched the MediaWiki master DC in etcd and in the MediaWiki code.
    """
    discovery = conftool.Confctl('discovery')
    # 1: switch DNS discovery record for the new dc to on.
    # This will NOT trigger confd to change the DNS admin state as it will cause a validation error
    mw_records = '(appserver|api|imagescaler)-rw'
    discovery.update({'pooled': True}, dnsdisc=mw_records, name=dc_to)
    for obj in discovery.get(dnsdisc=mw_records, name=dc_to):
        if not obj.pooled:
            logger.error("DNS discovery record %s is not pooled", obj.key)
            return 1

    # 2: Deploy the MediaWiki change already merged on the deployment server in pre-flight phase
    filename = 'CommonSettings'
    message = 'Switch MediaWiki active datacenter to {dc_to}'.format(dc_to=dc_to)
    expected = "$wmfMasterDatacenter = '{dc_to}';".format(dc_to=dc_to)
    if not mediawiki.check_config_line(filename, expected):
        mediawiki.scap_sync_config_file(filename, message)
        if not mediawiki.check_config_line(filename, expected):
            logger.error('Datacenter not changed in the MediaWiki config?')
            return 1

    # 3: switch off the old dc in conftool so that DNS discovery will be fixed
    discovery.update({'pooled': False}, dnsdisc=mw_records, name=dc_from)
    for obj in discovery.get(dnsdisc=mw_records, name=dc_from):
        if obj.pooled:
            logger.error("DNS discovery record %s is still pooled", obj.key)
            return 1
