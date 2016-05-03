from .. import env
from ..exceptions import EnvironmentFileNotFound


class YamlFileSpec(object):
    _environment = None

    def __init__(self, filename=None, **kwargs):
        self.filename = filename
        self.msg = None

    def can_handle(self):
        try:
            self._environment = env.from_file(self.filename)
            return True
        except EnvironmentFileNotFound as e:
            self.msg = str(e)
            return False

    @property
    def environment(self):
        if not self._environment:
            self.can_handle()
        return self._environment
