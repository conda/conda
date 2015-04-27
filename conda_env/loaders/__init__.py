import importlib
from ..exceptions import CondaEnvException
ENTRY_POINT = 'conda_env.loaders'
LOADERS = ['binstar']


class InvalidLoader(Exception):
    def __init__(self, name):
        msg = 'Unable to load installer for {}'.format(name)
        super(InvalidLoader, self).__init__(msg)


def get_loader(handle):
    for loader_name in LOADERS:
        try:
            loader_cls = importlib.import_module(ENTRY_POINT + '.' + loader_name)
            loader = loader_cls.get_instance(handle)
            if loader.can_download():
                return loader

        except ImportError:
            raise InvalidLoader(handle)

        except CondaEnvException, e:
            print e.message
