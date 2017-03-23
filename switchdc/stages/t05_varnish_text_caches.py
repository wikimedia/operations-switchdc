from switchdc.lib import remote

__title__ = 'Enable Puppet and force a run to get updated config on Varnish text caches'


def execute(dc_from, dc_to):
    """Enable Puppet and force a run to get updated config on Varnish text caches."""
    rc, _ = remote.run('R:Class = Role::Cache::Text', 'async',
                       ['puppet agent --enable', remote.get_puppet_agent_command()],
                       batch_size=30)

    return rc
