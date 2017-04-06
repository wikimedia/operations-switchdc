from switchdc.lib.remote import Remote

__title__ = "Rolling restart parsoid in eqiad and codfw"


def execute(dc_from, dc_to):
    from_servers = Remote(site=dc_from)
    from_servers.sync('restart-parsoid', batch_size=1, batch_sleep=15)
    to_servers = Remote(site=dc_to)
    to_servers.sync('restart-parsoid', batch_size=1, batch_sleep=15)
