import importlib
ENTRY_POINT = 'conda_env.installers'


class InvalidInstaller(Exception):
    def __init__(self, name):
        msg = f"Unable to load installer for {name}"
        super().__init__(msg)


def get_installer(name):
    try:
        return importlib.import_module(ENTRY_POINT + '.' + name)
    except ImportError:
        raise InvalidInstaller(name)
