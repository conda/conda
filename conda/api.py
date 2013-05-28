import base64
import hashlib

import conda.config as config
from conda.remote import fetch_repodata



def get_index():
    """
    return the index of packages available on the channels
    """
    channel_urls = config.get_channel_urls()

    index = {}
    for url in reversed(channel_urls):
        repodata = fetch_repodata(url)

        new_index = repodata['packages']
        for info in new_index.itervalues():
            info['channel'] = url
            # TODO: icons should point to separate files
            if 'icon' in info:
                md5 = info['icon']
                icondata = base64.b64decode(repodata['icons'][md5])
                assert hashlib.md5(icondata).hexdigest() == md5
                info['icon'] = icondata
        index.update(new_index)

    return index


def get_app_index():
    return {fn: info for fn, info in get_index().iteritems()
            if info.get('type') == 'app'}


def remaining_packages(fn):
    """
    given the filename of a package, return which packages (and their sizes)
    still need to be downloaded, in order to install the package.  That is,
    the package itself and it's dependencies (unless already in cache).
    Returns a list of tuples, (fn, size)
    """
    # TODO
    return


def launch_app(app_dir, add_args):
    return


def is_installed(fn):
    return # list of envs where app is installed


def install(fn):
    # link the app `fn` into a new environment and return the environments name
    return


if __name__ == '__main__':
    from pprint import pprint
    pprint(get_index())
