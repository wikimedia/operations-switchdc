from switchdc import SwitchdcError
from switchdc.lib import mysql
from switchdc.lib.remote import Remote

__title__ = "Update Tendril configuration for the new masters"


def execute(dc_from, dc_to):

    tendril = Remote()
    tendril.select('R:Class = Role::Mariadb::Tendril')

    commands = []
    for shard in mysql.CORE_SHARDS:
        remote = mysql.get_db_remote(dc_to, group='core', role='master', shard=shard)
        if len(remote.hosts) > 1:
            raise SwitchdcError("Expected to find only one host for core DB of shard {shard} in {dc}".format(
                shard=shard, dc=dc_to))

        master = remote.hosts[0]
        commands.append(mysql.get_query_command(
            ("UPDATE shards SET master_id = (SELECT id FROM servers WHERE host = '{master}') WHERE"
             "name = '{shard}'").format(master=master, shard=shard), database='tendril'))

    tendril.sync(*commands)
