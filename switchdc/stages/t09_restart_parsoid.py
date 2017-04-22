from switchdc.lib.remote import Remote

__title__ = 'Rolling restart of parsoid in {dc_from} and {dc_to}'


def execute(dc_from, dc_to):
    from_servers = Remote(site=dc_from)
    from_servers.select('R:class = role::parsoid')
    from_servers.sync('restart-parsoid', batch_size=1, batch_sleep=15.0)
    to_servers = Remote(site=dc_to)
    to_servers.select('R:class = role::parsoid')
    to_servers.sync('restart-parsoid', batch_size=1, batch_sleep=15.0)
