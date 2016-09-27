# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import re
import socket
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

from requests.packages.urllib3.util.url import parse_url, Url
from requests.packages.urllib3.exceptions import LocationParseError

from .._vendor.auxlib.decorators import memoize

log = getLogger(__name__)


def path_to_url(path):
    path = abspath(expanduser(path))
    url = urljoin('file:', pathname2url(path))
    log.debug("%s converted to %s", path, url)
    return url


def url_to_path(url):  # NOQA
    """Convert a file:// URL to a path."""
    assert url.startswith('file:'), "You can only turn file: urls into filenames (not %r)" % url
    path = url[len('file:'):].lstrip('/')
    path = unquote(path)
    if re.match('^([a-z])[:|]', path, re.I):
        path = path[0] + ':' + path[2:]
    elif not path.startswith(r'\\'):
        # if not a Windows UNC path
        path = '/' + path
    return path


def add_username_and_pass_to_url(url, username, passwd):
    url_obj = parse_url(url)
    url_obj.auth = username + ':' + quote(passwd, '')
    return url_obj.url


@memoize
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


def is_ipv4_address(string_ip):
    try:
        socket.inet_aton(string_ip)
    except socket.error:
        return False
    return True


def is_ipv6_address(string_ip):
    try:
        socket.inet_pton(socket.AF_INET6, string_ip)
    except socket.error:
        return False
    return True


def is_ip_address(string_ip):
    return is_ipv4_address(string_ip) or is_ipv6_address(string_ip)


def replace_path(url_parts, new_path):
    # Url ['scheme', 'auth', 'host', 'port', 'path', 'query', 'fragment']
    return Url(url_parts.scheme, url_parts.auth, url_parts.host, url_parts.port, new_path,
               url_parts.query, url_parts.fragment)


def replace_host(url_parts, new_host):
    # Url ['scheme', 'auth', 'host', 'port', 'path', 'query', 'fragment']
    return Url(url_parts.scheme, url_parts.auth, new_host, url_parts.port, url_parts.path,
               url_parts.query, url_parts.fragment)


def join(*args):
    return '/'.join(x.strip('/') for x in args)


join_url = join


def strip_scheme(url):
    return url.split('://', 1)[-1]


def split_anaconda_token(url):
    """
    Examples:
        >>> split_anaconda_token("https://1.2.3.4/t/tk-123-456/path")
        (u'https://1.2.3.4/path', u'tk-123-456')
        >>> split_anaconda_token("https://1.2.3.4/t//path")
        (u'https://1.2.3.4/path', u'')
        >>> split_anaconda_token("https://some.domain/api/t/tk-123-456/path")
        (u'https://some.domain/api/path', u'tk-123-456')
        >>> split_anaconda_token("https://1.2.3.4/conda/t/tk-123-456/path")
        (u'https://1.2.3.4/conda/path', u'tk-123-456')
        >>> split_anaconda_token("https://1.2.3.4/path")
        (u'https://1.2.3.4/path', None)
    """
    _token_match = re.search(r'/t/([a-zA-Z0-9-]*)', url)
    token = _token_match.groups()[0] if _token_match else None
    cleaned_url = url.replace('/t/' + token, '', 1) if token is not None else url
    return cleaned_url, token


def split_scheme_auth_token(url):
    if not url:
        return None, None, None, None
    cleaned_url, token = split_anaconda_token(url)
    url_parts = urlparse(cleaned_url)
    remainder_url = Url(host=url_parts.host, port=url_parts.port, path=url_parts.path,
                        query=url_parts.query).url
    return remainder_url, url_parts.scheme, url_parts.auth, token


if __name__ == "__main__":
    import doctest
    doctest.testmod()
