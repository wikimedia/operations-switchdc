import time

from switchdc.lib.dnsdisc import Discovery

__title__ = 'Reduce the TTL of all the MediaWiki read-write discovery records'


def execute(dc_from, dc_to):
    """Reduce the ttl on all appservers rw discovery entries."""
    ttl = Discovery('appservers-rw', 'api-rw', 'imagescaler-rw')
    ttl.update_ttl(10)
    # Verify
    time.sleep(5)
    ttl.check_ttl(10)
