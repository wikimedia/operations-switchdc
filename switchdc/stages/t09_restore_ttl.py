import time

from switchdc.lib.dnsdisc import Discovery

__title__ = 'Restore the TTL of all the MediaWiki read-write discovery records'


def execute(dc_from, dc_to):
    """Restore the original ttl on all appservers rw discovery entries"""
    ttl = Discovery('appservers-rw', 'api-rw', 'imagescaler-rw')
    ttl.update_ttl(300)
    # Verify
    time.sleep(5)
    ttl.check_ttl(300)
