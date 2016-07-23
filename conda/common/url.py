# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import re
from logging import getLogger
from os.path import abspath

try:
    # Python 3
    from urllib.parse import quote, unquote, urlunparse  # NOQA
except ImportError:
    # Python 2
    from urllib import quote, unquote
    from urlparse import urlunparse  # NOQA

from requests.packages.urllib3.util.url import parse_url
from requests.packages.urllib3.exceptions import LocationParseError

from ..utils import on_win

log = getLogger(__name__)


def path_to_url(path):
    path = abspath(path)
    if on_win:
        path = '/' + path.replace(':', '|').replace('\\', '/')
    return 'file://%s' % path


_url_drive_re = re.compile('^([a-z])[:|]', re.I)
def url_to_path(url):  # NOQA
    """Convert a file:// URL to a path."""
    assert url.startswith('file:'), "You can only turn file: urls into filenames (not %r)" % url
    path = url[len('file:'):].lstrip('/')
    path = unquote(path)
    if _url_drive_re.match(path):
        path = path[0] + ':' + path[2:]
    elif not path.startswith(r'\\'):
        # if not a Windows UNC path
        path = '/' + path
    return path


def add_username_and_pass_to_url(url, username, passwd):
    url_obj = parse_url(url)
    url_obj.auth = username + ':' + quote(passwd, '')
    return url_obj.url


def urlparse(url):
    return parse_url(url)


def url_to_s3_info(url):
    """
    Convert a S3 url to a tuple of bucket and key
    """
    parsed_url = parse_url(url)
    assert parsed_url.scheme == 's3', "You can only use s3: urls (not %r)" % url
    bucket, key = parsed_url.host, parsed_url.path
    return bucket, key


def is_url(url):
    try:
        p = urlparse(url)
        return p.netloc is not None or p.scheme == "file"
    except LocationParseError:
        log.debug("Could not parse url ({0}).".format(url))
        return False
