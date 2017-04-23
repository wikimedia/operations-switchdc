import time

from switchdc.lib.dnsdisc import Discovery
from switchdc.lib.remote import Remote

__title__ = 'Restore the TTL of all the MediaWiki read-write discovery records and cleanup confd stale files'


def execute(dc_from, dc_to):
    """Restore the original TTL of all the MediaWiki read-write discovery records and cleanup confd stale files."""
    ttl = Discovery('appservers-rw', 'api-rw', 'imagescaler-rw')
    ttl.update_ttl(300)
    # Verify
    time.sleep(5)
    ttl.check_ttl(300)

    remote = Remote()
    remote.select('R:class = authdns')  # Include both authdns::server and authdns::testns
    remote.sync('rm -fv /var/run/confd-template/.discovery-{appservers,api,imagescaler}-rw.state*.err')
