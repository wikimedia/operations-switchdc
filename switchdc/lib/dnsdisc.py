import time

import dns.resolver

from switchdc import SwitchdcError
from switchdc.dry_run import is_dry_run
from switchdc.lib.confctl import Confctl
from switchdc.lib.remote import Remote
from switchdc.log import logger


class Discovery(object):
    def __init__(self, *records):
        nameservers = Remote.query('R:class = role::authdns::server')
        self.resolvers = {}
        self.discovery = Confctl('discovery')
        for nameserver in nameservers:
            resolver = dns.resolver.Resolver()
            resolver.nameservers = [rdata.address for rdata in dns.resolver.query(nameserver)]
            self.resolvers[nameserver] = resolver
        self.records = records

    def update_ttl(self, ttl):
        """Update the TTL for all records.

        Arguments:
        ttl -- the value of the new TTL
        """
        # DRY-RUN handled by confctl
        dnsdisc = '({regexp})'.format(regexp='|'.join(self.records))
        logger.debug('Updating the TTL of {dnsdisc} to {ttl} seconds'.format(dnsdisc=dnsdisc, ttl=ttl))
        self.discovery.update({'ttl': ttl}, dnsdisc=dnsdisc)

    def check_ttl(self, expected):
        """Check the TTL for all records.

        Arguments:
        ttl -- the expected TTL value
        """
        logger.debug('Checking that TTL={ttl} for {records}.discovery.wmnet records'.format(
            ttl=expected, records=self.records))

        for record in self.resolve():
            if not is_dry_run() and record.ttl != expected:
                logger.error("Expected TTL '{expected}', got '{ttl}'".format(expected=expected, ttl=record.ttl))
                raise SwitchdcError(1)

    def check_record(self, name, expected, attempts=3, sleep=3):
        """Check that a record resolve to the expected IP.

        Arguments:
        name     -- the record to check the resolution for.
        expected -- the expected record to compare the resolution to.
        """
        logger.debug('Checking that {name}.discovery.wmnet records matches {expected}'.format(
            name=name, expected=expected))

        # Getting the expected record from the first resolver
        address = self.resolvers[self.resolvers.keys()[0]].query(expected)[0].address

        for i in xrange(attempts):
            logger.debug('Attempt {attempt} to check resolution for record {record}'.format(attempt=i, record=name))
            failed = False
            for record in self.resolve(name=name):
                if not is_dry_run() and record[0].address != address:
                    failed = True
                    logger.error("Expected IP '{expected}', got '{address}' for record {record}".format(
                        expected=address, address=record[0].address, record=name))

            if not failed:
                break
            elif i != (attempts - 1):  # Do not sleep after the last attempt
                time.sleep(sleep)
        else:
            raise SwitchdcError(1)

    def resolve(self, name=None):
        """Generator that yields the resolved records.

        Arguments:
        name -- optional record name to filter for.
        """
        if name is not None:
            records = [name]
        else:
            records = self.records

        for nameserver, resolver in self.resolvers.iteritems():
            for record in records:
                answer = resolver.query('{}.discovery.wmnet'.format(record))
                message = '{ns}:{rec}: {ip} TTL {ttl}'.format(
                    ns=nameserver, rec=record, ip=answer[0].address, ttl=answer.ttl)
                logger.debug(message)
                yield answer
