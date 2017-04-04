import dns.resolver

from switchdc import SwitchdcError
from switchdc.lib.confctl import Confctl
from switchdc.lib.remote import Remote
from switchdc.log import logger


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

    def update(self, expected):
        dnsdisc = '({regexp})'.format(regexp=self.records.join('|'))
        logger.info("Reducing the TTL of {} to {} seconds".format(dnsdisc, expected))
        self.discovery.update({'ttl': expected}, dnsdisc=dnsdisc)

    def check(self, expected):
        for nameserver, resolver in self.resolvers.items():
            for record in self.records:
                answer = resolver.query('{}.discovery.wmnet'.format(record))
                if answer.ttl != expected:
                    logger.error(
                        "TTL of {}.discovery.wmnet record on {} is {}".format(record, nameserver, answer.ttl))
                    raise SwitchdcError(1)
