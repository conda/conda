import conda.config as config
from conda.fetch import fetch_index



def get_index():
    """
    return the index of packages available on the channels
    """
    channel_urls = config.get_channel_urls()
    return fetch_index(channel_urls)


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
