import importlib
from ..exceptions import CondaEnvException, LoaderNotFound, InvalidLoader
ENTRY_POINT = 'conda_env.loaders'
LOADERS = ['binstar']


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

    raise LoaderNotFound(handle)
