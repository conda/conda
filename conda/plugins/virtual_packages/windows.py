import platform

from .. import hookimpl, CondaVirtualPackage


@hookimpl
def conda_virtual_packages():
    if platform.system() != "Windows":
        return

    yield CondaVirtualPackage("win", None, None)
