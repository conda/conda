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


if __name__ == '__main__':
    from pprint import pprint
    pprint(get_index())
