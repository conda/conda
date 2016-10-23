from __future__ import absolute_import, division, print_function, unicode_literals

from .core.index import get_index
from .resolve import Resolve

def get_package_versions(package):
    index = get_index()
    r = Resolve(index)
    return r.get_pkgs(package, emptyok=True)
