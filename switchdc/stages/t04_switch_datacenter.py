import os

import requests

from switchdc import conftool
from switchdc.remote import Remote
from switchdc.stages import get_module_config
from switchdc.log import logger

__title__ = "Switch MediaWiki configuration to the new datacenter"

config = get_module_config(__name__)


def check_mw_active_dc(dc):
    noc_server = config.get('noc_server', 'terbium.eqiad.wmnet')
    expected = "$wmfMasterDatacenter = '{}';".format(dc)
    try:
        mwconfig = requests.get('http://{}/conf/CommonSettings.php.txt'.format(noc_server),
                                headers={'host': 'noc.wikimedia.org'})
    except Exception:
        return False
    return (expected in mwconfig.text)


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

    # 2: Deploy the MediaWiki change already merged on tin in pre-flight phase
    if not check_mw_active_dc(dc_to):
        deployment_server = Remote(site=dc_to)
        deployment_server.select('R:class = role::deployment::server')
        # TODO: Verify this is correct
        user = os.getlogin()
        deployment_server.sync('su - {} scap sync-file wmf-config/CommonSettings.php "Dc Switchover"'.format(user))
        if not check_mw_active_dc(dc_to):
            logger.error('Datacenter not changed in the MediaWiki code?')
            return 1

    # 3: switch off the old dc in conftool so that DNS discovery will be fixed
    discovery.update({'pooled': False}, dnsdisc=mw_records, name=dc_from)
    for obj in discovery.get(dnsdisc=mw_records, name=dc_from):
        if obj.pooled:
            logger.error("DNS discovery record %s is still pooled", obj.key)
            return 1
