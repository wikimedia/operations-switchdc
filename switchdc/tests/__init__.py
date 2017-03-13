import os

import docker
import docker.errors

base_config_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'fixtures')


class DockerManager(object):

    def __init__(self, configdir, label, tag='latest'):
        self.datadir = os.path.join(configdir, 'stages.d', label)
        self.Dockerfile = os.path.join(self.datadir, 'Dockerfile')
        self.client = docker.from_env(version='auto')
        self.tag = u'switchdc_test/{}:{}'.format(label, tag)
        try:
            self.client.images.get(self.tag)
        except docker.errors.ImageNotFound:
            self.build_image()
        self.managed_containers = set()

    def build_image(self):
        ddir = self.datadir + os.path.sep
        self.client.images.build(
            path=ddir,
            tag=self.tag,
            rm=True
        )

    def run(self, name, *args, **kwargs):
        try:
            container = self.client.containers.get(name)
            if container.status == 'running':
                return
            else:
                container.start()
        except docker.errors.NotFound:
            self.client.containers.run(self.tag, None, name=name, *args, **kwargs)
        self.managed_containers.add(name)

    def stop(self, name):
        try:
            container = self.client.containers.get(name)
            if container.status == 'running':
                container.kill()
        except docker.errors.NotFound:
            pass

    def cleanup(self):
        """
        Stop any running container managed via this class
        """
        for container in list(self.managed_containers):
            self.stop(container)
            try:
                self.client.containers.get(container).remove()
            except docker.errors.NotFound:
                pass
            self.managed_containers.remove(container)
