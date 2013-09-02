from __future__ import print_function, division, absolute_import

import os
from os.path import dirname, isdir, isfile, join

from conda import config
from conda import install
from conda.utils import url_path
from conda.naming import fn2spec
from conda.fetch import fetch_index
from conda.compat import iteritems


def get_index(channel_urls=(), prepend=True):
    """
    Return the index of packages available on the channels

    If prepend=False, only the channels passed in as arguments are used.
    """
    channel_urls = config.normalize_urls(channel_urls)
    if prepend:
        channel_urls += config.get_channel_urls()
    return fetch_index(tuple(channel_urls))


def app_get_index():
    """
    return the index of available applications on the channels
    """
    index = get_index()
    return {fn: info for fn, info in iteritems(index)
            if info.get('type') == 'app'}


def app_get_icon_url(fn):
    """
    return the URL belonging to the icon for application `fn`.
    """
    index = get_index()
    info = index[fn]
    base_url = dirname(info['channel'].rstrip('/'))
    icon_fn = info['icon']
    icon_cache_path = join(config.pkgs_dir, 'cache', icon_fn)
    if isfile(icon_cache_path):
        return url_path(icon_cache_path)
    else:
        return '%s/icons/%s' % (base_url, icon_fn)


def app_info_packages(fn):
    """
    given the filename of a package, return which packages (and their sizes)
    still need to be downloaded, in order to install the package.  That is,
    the package itself and it's dependencies.
    Returns a list of tuples (pkg_name, pkg_version, size,
    fetched? True or False).
    """
    from conda.resolve import Resolve

    index = get_index()
    r = Resolve(index)
    res = []
    for fn2 in r.solve([fn2spec(fn)]):
        info = index[fn2]
        res.append((info['name'], info['version'], info['size'],
                    install.is_fetched(config.pkgs_dir, fn2[:-8])))
    return res


def app_is_installed(fn):
    """
    Return the list of prefix directories in which `fn` in installed into,
    which might be an empty list.
    """
    prefixes = [config.root_dir]
    for fn2 in os.listdir(config.envs_dir):
        prefix = join(config.envs_dir, fn2)
        if isdir(prefix):
            prefixes.append(prefix)
    dist = fn[:-8]
    return [prefix for prefix in prefixes if install.is_linked(prefix, dist)]

# It seems to me that we need different types of apps, i.e. apps which
# are preferably installed (or already exist) in existing environments,
# and apps which are more "standalone" (such as firefox).

def app_install(fn, prefix=config.root_dir):
    """
    Install the application `fn` into prefix (which defauts to the root
    environment).
    """
    import conda.plan as plan

    index = get_index()
    actions = plan.install_actions(prefix, index, [fn2spec(fn)])
    plan.execute_actions(actions, index)


def app_launch(fn, prefix=config.root_dir, additional_args=None):
    """
    Launch the application `fn` (with optional additional command line
    arguments), in the prefix (which defaults to the root environment).
    Returned is the process object (the one returned by subprocess.Popen),
    or None if the application `fn` is not installed in the prefix.
    """
    from conda.misc import launch

    return launch(fn, prefix, additional_args)


def app_uninstall(fn, prefix=config.root_dir):
    """
    Uninstall application `fn` (but not its dependencies).

    Like `conda remove fn`.

    """
    import conda.cli.common as common
    import conda.plan as plan

    index = None
    specs = [fn2spec(fn)]
    if (plan.is_root_prefix(prefix) and
        common.names_in_specs(common.root_no_rm, specs)):
        raise ValueError("Cannot remove %s from the root environment" %
            ', '.join(common.root_no_rm))

    actions = plan.remove_actions(prefix, specs)

    if plan.nothing_to_do(actions):
        raise ValueError("Nothing to do")

    plan.execute_actions(actions, index)


if __name__ == '__main__':
    #from pprint import pprint
    #pprint(missing_packages('twisted-12.3.0-py27_0.tar.bz2'))
    #print(app_install('twisted-12.3.0-py27_0.tar.bz2'))
    #pprint(get_index())
    print(app_get_icon_url('spyder-app-2.2.0-py27_0.tar.bz2'))
