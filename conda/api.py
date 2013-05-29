from os.path import isfile, isdir, join

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


def _fn2spec(fn):
    return ' '.join(fn[:-8].rsplit('-', 2))


def missing_packages(fn):
    """
    given the filename of a package, return which packages (and their sizes)
    still need to be downloaded, in order to install the package.  That is,
    the package itself and it's dependencies (unless already in cache).
    Returns a list of tuples (pkg_name, pkg_version, size).
    """
    from resolve import Resolve

    index = get_index()
    r = Resolve(index)
    res = []
    for fn2 in r.solve([_fn2spec(fn)]):
        if isfile(join(config.pkgs_dir, fn2[:-8], 'info', 'extracted')):
            status = 'cached'
        else:
            status = 'missing'
        info = index[fn2]
        res.append((status, info['name'], info['version'], info['size']))
    return res


def launch_app(app_dir, add_args):
    return


def is_installed(fn):
    return # list of envs where app is installed


def install(fn):
    import plan

    for i in xrange(1000):
        prefix = join(config.envs_dir, '%s-%03d' % (plan.name_dist(fn), i))
        if not isdir(prefix):
            break

    index = get_index()
    actions = plan.install_actions(prefix, index, [_fn2spec(fn)])
    plan.execute_actions(actions, index)
    return prefix


if __name__ == '__main__':
    from pprint import pprint
    #pprint(missing_packages('twisted-12.3.0-py27_0.tar.bz2'))
    print install('twisted-12.3.0-py27_0.tar.bz2')
