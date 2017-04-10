import dns.resolver

from switchdc import SwitchdcError
from switchdc.dry_run import is_dry_run
from switchdc.lib.confctl import Confctl
from switchdc.lib.remote import Remote
from switchdc.log import log_dry_run, logger


class DiscoveryTTL(object):
    def __init__(self, *records):
        nameservers = Remote.query('R:class = role::authdns::server')
        self.resolvers = {}
        self.discovery = Confctl('discovery')
        for nameserver in nameservers:
            resolver = dns.resolver.Resolver()
            resolver.nameservers = [rdata.address for rdata in dns.resolver.query(nameserver)]
            self.resolvers[nameserver] = resolver
        self.records = records

    def update(self, ttl):
        # DRY-RUN handled by confctl
        dnsdisc = '({regexp})'.format(regexp='|'.join(self.records))
        logger.info("Reducing the TTL of {dnsdisc} to {ttl} seconds".format(dnsdisc=dnsdisc, ttl=ttl))
        self.discovery.update({'ttl': ttl}, dnsdisc=dnsdisc)

    def check(self, expected):
        for nameserver, resolver in self.resolvers.items():
            for record in self.records:
                answer = resolver.query('{}.discovery.wmnet'.format(record))

                if is_dry_run():
                    log_dry_run("{ns}:{rec}: {ip} TTL {ttl}".format(
                        ns=nameserver, rec=record, ip=[r.address for r in answer][0], ttl=answer.ttl))
                    continue

                if answer.ttl != expected:
                    logger.error(
                        "TTL of {}.discovery.wmnet record on {} is {}".format(record, nameserver, answer.ttl))
                    raise SwitchdcError(1)
