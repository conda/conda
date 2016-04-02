from __future__ import print_function, division, absolute_import

import os
from collections import defaultdict
from os.path import isdir, join

from conda import config
from conda import install
from conda.fetch import fetch_index
from conda.compat import iteritems, itervalues
from conda.resolve import Package, Resolve


def _name_fn(fn):
    assert fn.endswith('.tar.bz2')
    return install.name_dist(fn[:-8])

def _fn2spec(fn):
    assert fn.endswith('.tar.bz2')
    return ' '.join(fn[:-8].rsplit('-', 2)[:2])

def _fn2fullspec(fn):
    assert fn.endswith('.tar.bz2')
    return ' '.join(fn[:-8].rsplit('-', 2))


def get_index(channel_urls=(), prepend=True, platform=None,
              use_cache=False, unknown=False, offline=False,
              prefix=None):
    """
    Return the index of packages available on the channels

    If prepend=False, only the channels passed in as arguments are used.
    If platform=None, then the current platform is used.
    If prefix is supplied, then the packages installed in that prefix are added.
    """
    channel_urls = config.normalize_urls(channel_urls, platform, offline)
    if prepend:
        pri0 = max(itervalues(channel_urls)) if channel_urls else 0
        for url, rec in iteritems(config.get_channel_urls(platform, offline)):
            channel_urls[url] = (rec[0], rec[1] + pri0)
    index = fetch_index(channel_urls, use_cache=use_cache, unknown=unknown)
    if prefix:
        for dist, info in iteritems(install.linked_data(prefix)):
            fn = dist + '.tar.bz2'
            channel = info.get('channel', '')
            url_s, priority = channel_urls.get(channel, (channel, 0))
            key = url_s + '::' + fn if url_s else fn
            if key not in index:
                # only if the package in not in the repodata, use local
                # conda-meta (with 'depends' defaulting to [])
                info.setdefault('depends', [])
                info['fn'] = fn
                info['schannel'] = url_s
                info['channel'] = channel
                info['url'] = channel + fn
                info['priority'] = priority
                index[key] = info
    return index


##########################################################################
# NOTE: All functions starting with 'app_' in this module are deprecated
#       and should no longer be used.
##########################################################################
def app_get_index(all_version=False):
    """
    return the index of available applications on the channels

    By default only the latest version of each app is included in the result,
    unless all_version is set to True.
    """
    import sys
    pyxx = 'py%d%d' % sys.version_info[:2]

    def filter_build(build):
        return bool(pyxx in build) if 'py' in build else True

    index = {fn: info for fn, info in iteritems(get_index())
             if info.get('type') == 'app' and filter_build(info['build'])}
    if all_version:
        return index

    d = defaultdict(list)  # name -> list of Package objects
    for fn, info in iteritems(index):
        d[_name_fn(fn)].append(Package(fn, info))

    res = {}
    for pkgs in itervalues(d):
        pkg = max(pkgs)
        res[pkg.fn] = index[pkg.fn]
    return res


def app_get_icon_url(fn):
    """
    return the URL belonging to the icon for application `fn`.
    """
    from conda.misc import make_icon_url
    index = get_index()
    info = index[fn]
    return make_icon_url(info)


def app_info_packages(fn, prefix=config.root_dir):
    """
    given the filename of a package, return which packages (and their sizes)
    still need to be downloaded, in order to install the package.  That is,
    the package itself and it's dependencies.
    Returns a list of tuples (pkg_name, pkg_version, size,
    fetched? True or False).
    """
    from conda.resolve import Resolve

    index = get_index(prefix=prefix)
    r = Resolve(index)
    res = []
    for fn2 in r.solve([_fn2fullspec(fn)], installed=install.linked(prefix)):
        info = index[fn2]
        if 'link' not in info:
            res.append((info['name'], info['version'], info['size'],
                        any(install.is_fetched(pkgs_dir, fn2[:-8])
                            for pkgs_dir in config.pkgs_dirs)))
    return res


def app_is_installed(fn, prefixes=None):
    """
    Return the list of prefix directories in which `fn` in installed into,
    which might be an empty list.
    """
    if prefixes is None:
        prefixes = [config.root_dir]
        for envs_dir in config.envs_dirs:
            for fn2 in os.listdir(envs_dir):
                prefix = join(envs_dir, fn2)
                if isdir(prefix):
                    prefixes.append(prefix)
    dist = fn[:-8]
    return [p for p in prefixes if install.is_linked(p, dist)]

# It seems to me that we need different types of apps, i.e. apps which
# are preferably installed (or already exist) in existing environments,
# and apps which are more "standalone" (such as firefox).

def app_install(fn, prefix=config.root_dir):
    """
    Install the application `fn` into prefix (which defauts to the root
    environment).
    """
    import conda.plan as plan

    index = get_index(prefix=prefix)
    actions = plan.install_actions(prefix, index, [_fn2spec(fn)])
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

    index = get_index(prefix=prefix)
    specs = [_fn2spec(fn)]
    if (plan.is_root_prefix(prefix) and
            common.names_in_specs(common.root_no_rm, specs)):
        raise ValueError("Cannot remove %s from the root environment" %
                         ', '.join(common.root_no_rm))

    actions = plan.remove_actions(prefix, specs, index=index)

    if plan.nothing_to_do(actions):
        raise ValueError("Nothing to do")

    plan.execute_actions(actions, index)


def get_package_versions(package, offline=False):
    index = get_index(offline=offline)
    r = Resolve(index)
    return r.get_pkgs(package, emptyok=True)


if __name__ == '__main__':
    for fn in app_get_index():
        print('%s: %s' % (fn, app_is_installed(fn)))
