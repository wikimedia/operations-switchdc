from switchdc.lib.remote import Remote

__title__ = 'Enable Puppet and force a run to get updated config on Varnish text caches'


def execute(dc_from, dc_to):
    """Enable Puppet and force a run to get updated config on Varnish text caches."""
    remote = Remote()
    remote.select('R:Class = Role::Cache::Text')
    rc = remote.async('puppet agent --enable', remote.get_puppet_agent_command(), batch_size=30)

    return rc
