import pluggy
from . import archspec, cuda, linux, osx, windows


def register(pm: pluggy.PluginManager) -> None:
    """
    Please add a nice doc string too explaining why this function exists!
    """
    pm.register(archspec)
    pm.register(cuda)
    pm.register(linux)
    pm.register(osx)
    pm.register(windows)
