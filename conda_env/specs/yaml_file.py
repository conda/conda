from .. import env


class YamlFileSpec(object):
    _environment = None

    def __init__(self, filename=None, name=None, **kwargs):
        self.filename = filename
        self.name = name

    def can_handle(self):
        self._environment = env.from_file(self.filename)
        return True

    @property
    def environment(self):
        if not self._environment:
            self.can_handle()
        return self._environment
