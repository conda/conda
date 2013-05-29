from os.path import isfile, join

from utils import memoized

import conda.config as config
from conda.fetch import fetch_index


@memoized
def get_index():
    """
    return the index of packages available on the channels
    """
    channel_urls = config.get_channel_urls()
    return fetch_index(channel_urls)


def get_app_index():
    index = get_index()
    return {fn: info for fn, info in index.iteritems()
            if info.get('type') == 'app'}


def remaining_packages(fn):
    """
    given the filename of a package, return which packages (and their sizes)
    still need to be downloaded, in order to install the package.  That is,
    the package itself and it's dependencies (unless already in cache).
    Returns a list of tuples (fn, size).
    """
    from resolve import Resolve

    spec = ' '.join(fn[:-8].rsplit('-', 2))
    index = get_index()
    r = Resolve(index)
    res = []
    for fn2 in r.solve([spec]):
        if isfile(join(config.pkgs_dir, fn2[:-8], 'info', 'extracted')):
            continue
        res.append((fn2, index[fn2]['size']))
    return res


def launch_app(app_dir, add_args):
    return


def is_installed(fn):
    return # list of envs where app is installed


def install(fn):
    # link the app `fn` into a new environment and return the environments name
    return


if __name__ == '__main__':
    from pprint import pprint
    pprint(remaining_packages('twisted-12.3.0-py27_0.tar.bz2'))
