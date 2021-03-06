import re

from conftool import configuration, kvobject, loader
from conftool.drivers import BackendError

from switchdc import SwitchdcError
from switchdc.dry_run import is_dry_run
from switchdc.log import logger


class ConfigError(SwitchdcError):
    """Custom exception class for errors of this module."""


class Confctl(object):

    def __init__(self, obj_type, config='/etc/conftool/config.yaml',
                 schema='/etc/conftool/schema.yaml'):
        self._schema = loader.Schema.from_file(schema)
        self.entity = self._schema.entities[obj_type]
        kvobject.KVObject.setup(configuration.get(config))

    def _select(self, tags):
        selectors = {}
        for tag, expr in tags.items():
            selectors[tag] = re.compile('^{}$'.format(expr))
        for obj in self.entity.query(selectors):
            yield obj

    def update(self, changed, **tags):
        """
        Updates the value of conftool objects corresponding to the selection
        done with tags.

        Example:
          confctl.update({'pooled': False}, service='appservers-.*', name='eqiad')
        """
        logger.debug('Updating conftool matching tags: {tags}'.format(tags=tags))

        for obj in self._select(tags):
            logger.debug('Updating conftool: {obj} -> {changed}'.format(obj=obj, changed=changed))

            if is_dry_run():
                continue

            try:
                obj.update(changed)
            except BackendError as e:
                logger.error("Error writing to etcd: %s", e)
                raise ConfigError(1)
            except Exception as e:
                logger.error("Generic error in conftool: %s", e)
                raise ConfigError(3)

    def get(self, **tags):
        """Gets conftool objects corresponding to the selection."""
        for obj in self._select(tags):
            logger.debug('Selected conftool object: {obj}'.format(obj=obj))
            yield obj
