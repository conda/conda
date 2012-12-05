# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
'''
This module is for backwards compatibility with the Launcher. All
functions contained are deprecated and should not be used for any
new development.
'''

from os import listdir, makedirs
from os.path import exists, join
from shutil import rmtree

from config import ROOT_DIR, PACKAGES_DIR
from install import activate, activated

ENVS_DIR = join(ROOT_DIR, 'envs')


def get_installed(prefix=ROOT_DIR):
    """
    Return the set of installed packages, where each element in the set is
    a tuple(name, version, build).  The optional argument prefix specifies
    the prefix for list of packages is returned.
    """
    canonical_names = activated(prefix)
    res = set()
    for name in sorted(canonical_names):
        res.add(tuple(name.rsplit('-', 2)))
    return res


def create_env(envname, dists):
    dir_name = join(ENVS_DIR, envname)
    makedirs(dir_name)
    for dist in dists:
        activate(PACKAGES_DIR, dist, dir_name)


def remove_env(envname):
    rmtree(join(ROOT_DIR, 'envs', envname))

def get_envs():
    return listdir(ENVS_DIR)


# TODO
def get_env_packages(envname):
    return get_installed(join(ENVS_DIR, envname))


def get_env_path(envname):
    dir_name = join(ENVS_DIR, envname)
    if not exists(dir_name): return ''
    return dir_name
