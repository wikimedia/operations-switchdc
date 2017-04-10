import time

from switchdc.lib.dnsdisc import DiscoveryTTL

__title__ = 'Reduce the TTL of all the MediaWiki discovery records'


def execute(dc_from, dc_to):
    """Reduce the ttl on all appservers rw discovery entries."""
    ttl = DiscoveryTTL('appservers-rw', 'api-rw', 'imagescaler-rw')
    ttl.update(10)
    # Verify
    time.sleep(5)
    ttl.check(10)
