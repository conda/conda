import tarfile
import logging
from os.path import isfile, join


log = logging.getLogger(__name__)


def extract(pkg, env):
    pass


def activate(pkg, env):
    '''
    set up link farm for the specified package, in the specified Anaconda
    environment
    '''
    bz2path = join(env.conda.packages_dir, pkg.filename)
    assert isfile(bz2path), bz2path

    t = tarfile.open(bz2path)
    t.extractall(env.prefix)
    t.close()


def deactivate(pkg, env):
    '''
    tear down link farm for the specified package, in the specified
    Anaconda environment
    '''
    return
