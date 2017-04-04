import time

import dns.resolver

from switchdc import SwitchdcError
from switchdc.lib.confctl import Confctl
from switchdc.lib.remote import Remote
from switchdc.log import logger

__title__ = "Reduce the TTL of all the MediaWiki discovery records"


def execute(dc_from, dc_to):
    """Reduce the ttl on """
    discovery = Confctl('discovery')
    logger.info("Reducing the TTL of all MediaWiki discovery records to 10 seconds")
    discovery.update({'ttl': 10}, dnsdisc='(appservers|api|imagescaler)-rw')

    # Verify
    time.sleep(5)
    for dns_master in Remote.query('R:class = role::authdns::server'):
        resolver = dns.resolver.Resolver()
        resolver.nameservers = [rdata.address for rdata in dns.resolver.query(dns_master)]
        for hostname in ['appservers-rw', 'api-rw', 'imagescaler-rw']:
            answer = resolver.query('{host}.discovery.wmnet'.format(host=hostname))
            if answer.ttl != 10:
                logger.error("TTL of {}.discovery.wmnet record on {} is {}".format(hostname, dns_master, answer.ttl))
                raise SwitchdcError(1)
