from switchdc.lib import puppet
from switchdc.lib.remote import Remote

__title__ = 'Enable Puppet and force a run to get updated config on Varnish text caches'


def execute(dc_from, dc_to):
    """Enable Puppet and force a run to get updated config on Varnish text caches."""
    remote = Remote()
    remote.select('R:Class = Role::Cache::Text')
    remote.async('puppet agent --enable', puppet.get_agent_run_command(), batch_size=30)
