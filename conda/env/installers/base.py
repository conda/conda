import importlib
ENTRY_POINT = 'conda_env.installers'


class InvalidInstaller(Exception):
    def __init__(self, name):
        msg = 'Unable to load installer for {}'.format(name)
        super(InvalidInstaller, self).__init__(msg)


def get_installer(name):
    try:
        return importlib.import_module(ENTRY_POINT + '.' + name)
    except ImportError:
        raise InvalidInstaller(name)
