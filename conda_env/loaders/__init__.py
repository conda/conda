import importlib
ENTRY_POINT = 'conda_env.loaders'
LOADERS = ['binstar']


class InvalidLoader(Exception):
    def __init__(self, name):
        msg = 'Unable to load installer for {}'.format(name)
        super(InvalidLoader, self).__init__(msg)


def get_loader(name):
    for loader_name in LOADERS:
        try:
            loader = importlib.import_module(ENTRY_POINT + '.' + loader_name)
            if loader.can_download(name):
                return loader
        except ImportError:
            raise InvalidLoader(name)
