from __future__ import print_function, division, absolute_import

import os
from collections import defaultdict
from os.path import isdir, join
from operator import itemgetter

from conda import config
from conda import install
from conda.fetch import fetch_index
from conda.compat import iteritems, itervalues
from conda.resolve import Package, Resolve


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
        pri0 = max(itervalues(channel_urls), key=itemgetter(1))[1] if channel_urls else 0
        for url, rec in iteritems(config.get_channel_urls(platform, offline)):
            channel_urls[url] = (rec[0], rec[1] + pri0)
    index = fetch_index(channel_urls, use_cache=use_cache, unknown=unknown)
    if prefix:
        for dist, info in iteritems(install.linked_data(prefix)):
            fn = dist + '.tar.bz2'
            channel = info.get('channel', '')
            if channel not in channel_urls:
                channel_urls[channel] = (config.canonical_channel_name(channel, True, True), 0)
            url_s, priority = channel_urls[channel]
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
        name = install.name_dist(fn[:-8])
        d[name].append(Package(fn, info))

    res = {}
    for pkgs in itervalues(d):
        pkg = max(pkgs)
        res[pkg.fn] = index[pkg.fn]
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

def get_package_versions(package, offline=False):
    index = get_index(offline=offline)
    r = Resolve(index)
    return r.get_pkgs(package, emptyok=True)


if __name__ == '__main__':
    for fn in app_get_index():
        print('%s: %s' % (fn, app_is_installed(fn)))
