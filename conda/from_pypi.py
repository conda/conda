from __future__ import print_function, division, absolute_import
from conda.resolve import MatchSpec, Resolve

def create_recipe(prefix, spec):
    pass

def build_pacakge(prefix, recipedir):
    pass

def install_package(prefix, pkgname):
    pass

def install_from_pypi(prefix, index, specs):
    r = Resolve(index)
    for_conda = []
    for s in specs:
        try:
            r.find_matches(MatchSpec(s)).next()
        except StopIteration:
            print("Conda package not available for %s, attempting to create one from pypi" % s)
            recipedir = create_recipe(prefix, s)
            pkgname = build_package(prefix, recipedir)
            install_package(prefix, pkgname)
        else:
            for_conda.append(s)            
    return for_conda
