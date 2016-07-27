# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import re
from logging import getLogger
from os.path import abspath, expanduser

try:
    # Python 3
    from urllib.parse import quote, unquote, urlunparse, urljoin  # NOQA
    from urllib.request import pathname2url
except ImportError:
    # Python 2
    from urllib import quote, unquote, pathname2url
    from urlparse import urlunparse, urljoin  # NOQA

from requests.packages.urllib3.util.url import parse_url
from requests.packages.urllib3.exceptions import LocationParseError

log = getLogger(__name__)


def path_to_url(path):
    path = abspath(expanduser(path))
    url = urljoin('file:', pathname2url(path))
    log.debug("%s converted to %s", path, url)
    return url


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
