import re

from conftool import configuration, loader, kvobject


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
        for obj in self._select(tags):
            obj.update(changed)

    def get(self, **tags):
        """
        Gets conftool objects corresponding to the selection
        """
        for obj in self._select(tags):
            yield obj
