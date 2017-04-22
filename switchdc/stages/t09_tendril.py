from switchdc import SwitchdcError
from switchdc.lib import mysql
from switchdc.lib.remote import Remote
from switchdc.log import logger

__title__ = 'Update Tendril tree to start from the core DB masters in {dc_to}'


def execute(dc_from, dc_to):

    tendril = Remote()
    tendril.select('R:Class = Role::Mariadb::Tendril')

    commands = []
    for shard in mysql.CORE_SHARDS:
        remote = mysql.get_db_remote(dc_to, group='core', role='master', shard=shard)
        if len(remote.hosts) > 1:
            logger.error('Expected to find only one host for core DB of shard {shard} in {dc}'.format(
                         shard=shard, dc=dc_to))
            raise SwitchdcError(1)

        master = remote.hosts[0]
        commands.append(mysql.get_query_command(
            ("UPDATE shards SET master_id = (SELECT id FROM servers WHERE host = '{master}') WHERE "
             "name = '{shard}'").format(master=master, shard=shard), database='tendril'))

    tendril.sync(*commands)
