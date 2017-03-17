from switchdc import remote
from switchdc.log import logger


class MysqlReadonlyError(Exception):
    """Custom exception class for errors of this module."""


def get_query_command(query, column_names=False):
    """Return the command to be executed for a given query.

    Arguments:
    query        -- the mysql query to be executed. Double quotes must be already escaped
    column_names -- wheter to include the column names or not in the output. [optional, default: False]
    """
    columns = ''
    if not column_names:
        columns = '--skip-column-names '

    return 'mysql --skip-ssl --batch {columns}-e "{query}"'.format(columns=columns, query=query)


def get_puppetdb_hosts_selection(dc, **kwargs):
    """Return the PuppetDB query selection string for databases to be used in Cumin.

    Arguments:
    dc     -- the name of the datacenter to filter for
    kwargs -- a dictionary of key: value for the parameters to be filtered in the Role::Mariadb::Groups puppet class.
    """
    query = '*.{dc}.wmnet and R:Class = Role::Mariadb::Groups'.format(dc=dc)
    for key, value in kwargs:
        query += ' and R:Class%mysql_{key} = "{value}"'.format(key=key, value=value)

    return query


def set_core_masters_readonly(dc, ro):
    """Set the core masters in read-only or read-write mode.

    Arguments:
    dc -- the name of the datacenter to filter for
    ro -- boolean to decide whether the read-only mode should be set or removed.
    """
    rc, _ = remote.run(get_puppetdb_hosts_selection(dc, group='core', role='master'),
                       'sync', [get_query_command('SET GLOBAL read_only={ro}'.format(ro=ro))])
    if rc != 0:
        logger.error("Failed to set masters read-only to '{ro}' on DC '{dc}'".format(ro=ro, dc=dc))
        raise MysqlReadonlyError


def verify_core_masters_readonly(dc, ro):
    """Verify that the core masters are in read-only or read-write mode.

    Arguments:
    dc -- the name of the datacenter to filter for
    ro -- boolean to check whether the read-only mode should be set or not.
    """
    rc, worker = remote.run(get_puppetdb_hosts_selection(dc, group='core', role='master'),
                            'sync', [get_query_command('SELECT @@global.read_only')])
    if rc != 0:
        raise MysqlReadonlyError

    failed = False
    for hosts, output in worker.get_results():
        if output != str(int(ro)):
            logger.error("Expected output to be '{expected}', got '{output}' for hosts {hosts}".format(
                expected=str(int(ro)), output=output, hosts=hosts))
            failed = True

    if failed:
        raise MysqlReadonlyError
