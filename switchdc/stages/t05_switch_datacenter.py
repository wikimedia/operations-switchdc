from switchdc import SwitchdcError
from switchdc.dry_run import is_dry_run
from switchdc.lib import mediawiki
from switchdc.lib.confctl import Confctl
from switchdc.lib.dnsdisc import Discovery
from switchdc.log import logger

__title__ = 'Switch MediaWiki master datacenter and read-write discovery records from {dc_from} to {dc_to}'


def execute(dc_from, dc_to):
    """Switchig the MediaWiki master DC in etcd for both DNS discovery and MediaWiki config."""
    # 1: switch DNS discovery record for the new dc to on.
    # This will NOT trigger confd to change the DNS admin state as it will cause a validation error
    discovery = Confctl('discovery')
    mw_records = '(appservers|api|imagescaler)-rw'
    discovery.update({'pooled': True}, dnsdisc=mw_records, name=dc_to)
    for obj in discovery.get(dnsdisc=mw_records, name=dc_to):
        if not obj.pooled and not is_dry_run():
            logger.error('DNS discovery record {record} is not pooled'.format(record=obj.key))
            raise SwitchdcError(1)

    # 2: Switch the MediaWiki config master DC
    mediawiki.set_master_datacenter(dc_to)
    mediawiki.check_siteinfo('.query.general["wmf-config"].wmfMasterDatacenter == "{dc_to}"'.format(dc_to=dc_to),
                             attempts=5)

    # 3: switch off the old dc in conftool so that DNS discovery will be fixed
    discovery.update({'pooled': False}, dnsdisc=mw_records, name=dc_from)
    for obj in discovery.get(dnsdisc=mw_records, name=dc_from):
        if obj.pooled and not is_dry_run():
            logger.error('DNS discovery record {record} is still pooled'.format(record=obj.key))
            raise SwitchdcError(1)

    # 4: verify that the IP of the records matches the expected one
    dns = Discovery('appservers-rw', 'api-rw', 'imagescaler-rw')
    dns.check_record('appservers-rw', 'appservers.svc.{dc_to}.wmnet'.format(dc_to=dc_to))
    dns.check_record('api-rw', 'api.svc.{dc_to}.wmnet'.format(dc_to=dc_to))
    dns.check_record('appservers-rw', 'rendering.svc.{dc_to}.wmnet'.format(dc_to=dc_to))
