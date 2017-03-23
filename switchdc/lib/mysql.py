from switchdc import SwitchdcError
from switchdc.log import logger
from switchdc.remote import Remote


class MysqlError(SwitchdcError):
    """Custom exception class for errors of this module."""


def get_query_command(query):
    """Return the command to be executed for a given query.

    Arguments:
    query        -- the mysql query to be executed. Double quotes must be already escaped
    column_names -- wheter to include the column names or not in the output. [optional, default: False]
    """
    return 'mysql --skip-ssl --skip-column-names --batch -e "{query}"'.format(query=query)


def get_db_remote(dc, **kwargs):
    """Return the Remote instance with selected hosts from Role::Mariadb::Groups to be used in Cumin.

    Arguments:
    dc     -- the name of the datacenter to filter for
    kwargs -- a dictionary of key: value for the parameters to be filtered in the Role::Mariadb::Groups puppet class.
    """
    remote = Remote(site=dc)
    query = 'R:Class = Role::Mariadb::Groups'
    for key, value in kwargs:
        query += ' and R:Class%mysql_{key} = "{value}"'.format(key=key, value=value)

    remote.select(query)
    return remote


def set_core_masters_readonly(dc, ro):
    """Set the core masters in read-only or read-write mode.

    Arguments:
    dc -- the name of the datacenter to filter for
    ro -- boolean to decide whether the read-only mode should be set or removed.
    """
    remote = get_db_remote(dc, group='core', role='master')
    remote.sync(get_query_command('SET GLOBAL read_only={ro}'.format(ro=ro)))


def verify_core_masters_readonly(dc, ro):
    """Verify that the core masters are in read-only or read-write mode.

    Arguments:
    dc -- the name of the datacenter to filter for
    ro -- boolean to check whether the read-only mode should be set or not.
    """
    remote = get_db_remote(dc, group='core', role='master')
    remote.sync(get_query_command('SELECT @@global.read_only'))

    failed = False
    for hosts, output in remote.worker.get_results():
        if output != str(int(ro)):
            logger.error("Expected output to be '{expected}', got '{output}' for hosts {hosts}".format(
                expected=str(int(ro)), output=output, hosts=hosts))
            failed = True

    if failed:
        raise MysqlError(1)


def ensure_core_masters_in_sync(dc_from, dc_to):
    """Ensure all core masters of dc_to are in sync with the core masters of dc_from.

    Arguments:
    dc_from -- the name of the datacenter from where to get the master positions
    dc_to   -- the name of the datacenter where to check that they are in sync
    """
    shards = ('s1', 's2', 's3', 's4', 's5', 's6', 's7', 'x1', 'es2', 'es3')

    for shard in shards:
        gtid = ''
        remote_from = get_db_remote(dc_from, group='core', role='master', shard=shard)
        remote_from.sync(get_query_command('SELECT @@GLOBAL.gtid_binlog_pos'))

        for host, output in remote_from.worker.get_results():
            if host == remote_from.hosts:
                gtid = output
                break
        else:
            raise MysqlError(1)

        remote_to = get_db_remote(dc_to, group='core', role='master', shard=shard)
        query = "SELECT MASTER_GTID_WAIT('{gtid}', 30)".format(gtid=gtid)  # Wait for master is in sync, fail after 30
        remote_to.sync(get_query_command(query))

        for host, output in remote_to.worker.get_results():
            if output != '0':  # See https://mariadb.com/kb/en/mariadb/master_gtid_wait/
                logger.error("GTID not in sync after timeout for host {host}".format(host=remote_to.hosts))
                raise MysqlError(2)
