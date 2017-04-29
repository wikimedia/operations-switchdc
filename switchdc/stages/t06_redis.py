from switchdc import SwitchdcError
from switchdc.log import logger
from switchdc.lib.redis_cluster import RedisShardsBase, RedisSwitchError
from switchdc.stages import get_module_config, get_module_config_dir

__title__ = 'Switch the Redis masters from {dc_from} to {dc_to} and invert the replication'

dirname = __name__.split('.')[-1]
config = get_module_config(dirname)
config_dir = get_module_config_dir(dirname)

REDIS_PASSWORD = config.get('redis_password', None)


class RedisShards(RedisShardsBase):

    def stop_replica(self, dc):
        for instance in self.shards[dc].values():
            if instance.is_master:
                logger.debug("Instance %s is already master, doing nothing", instance)
                continue
            try:
                logger.debug("Stopping replica on {instance}".format(instance=instance))
                if not self.dry_run:
                    instance.stop_replica()
            except Exception as e:
                logger.exception("Generic failure while stopping replica on %s: %s", instance, e)
                raise

            if not instance.is_master and not self.dry_run:
                logger.exception("Instance %s is still a slave of %s, aborting", instance, instance.slave_of)
                raise RedisSwitchError(1)

    def start_replica(self, dc, dc_master):
        for shard, instance in self.shards[dc].items():
            master = self.shards[dc_master][shard]
            if instance.slave_of == str(master):
                logger.debug('Replica already configured on {instance}'.format(instance=instance))
            else:
                logger.debug('Starting replica {master} => {local}'.format(master=master, local=instance))
                if not self.dry_run:
                    instance.start_replica(master)

            if instance.slave_of != str(master) and not self.dry_run:
                logger.error("Replica on %s is not correctly configured", instance)
                raise RedisSwitchError(2)


def execute(dc_from, dc_to):
    """Switches the replication for both redis clusters for mediawiki (jobqueue and sessions)."""
    for cluster in ('jobqueue', 'sessions'):
        try:
            servers = RedisShards(cluster, config_dir, REDIS_PASSWORD)
        except Exception, e:
            logger.error("Failed loading redis data: %s", e, exc_info=True)
            raise SwitchdcError(1)

        # Now let's disable replication
        logger.info('Stopping replication for all instances in {dc}, cluster {cluster}'.format(
            dc=dc_to, cluster=cluster))
        try:
            servers.stop_replica(dc_to)
        except RedisSwitchError:
            raise
        except Exception as e:
            logger.exception('Failed to stop replication for all instances in %s, cluster %s: %s',
                             dc_to, cluster, e.message)
            raise SwitchdcError(3)

        logger.info('Starting replication for all instances in {dc}, cluster {cluster}'.format(
            dc=dc_from, cluster=cluster))
        try:
            servers.start_replica(dc_from, dc_to)
        except RedisSwitchError:
            raise
        except Exception:
            logger.exception('Failed to start replication for all instances in %s, cluster %s',
                             dc_to, cluster, e.message)
            raise SwitchdcError(4)
