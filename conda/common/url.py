# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import re
import socket
import sys
from getpass import getpass
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

from requests.packages.urllib3.exceptions import LocationParseError
from requests.packages.urllib3.util.url import Url, parse_url

from .._vendor.auxlib.decorators import memoize

log = getLogger(__name__)


on_win = bool(sys.platform == "win32")


@memoize
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


@memoize
def urlparse(url):
    if on_win and url.startswith('file:'):
        url.replace('\\', '/')
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
    start = '/' if not args[0] or args[0].startswith('/') else ''
    return start + '/'.join(y for y in (x.strip('/') for x in args if x) if y)


join_url = join


def has_scheme(value):
    return re.match(r'[a-z][a-z0-9]{0,11}://', value)


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
        >>> split_anaconda_token("https://10.2.3.4:8080/conda/t/tk-123-45")
        (u'https://10.2.3.4:8080/conda', u'tk-123-45')
    """
    _token_match = re.search(r'/t/([a-zA-Z0-9-]*)', url)
    token = _token_match.groups()[0] if _token_match else None
    cleaned_url = url.replace('/t/' + token, '', 1) if token is not None else url
    return cleaned_url.rstrip('/'), token


def split_platform(url):
    """

    Examples:
        >>> split_platform("https://1.2.3.4/t/tk-123/osx-64/path")
        (u'https://1.2.3.4/t/tk-123/path', u'osx-64')

    """
    from conda.base.constants import PLATFORM_DIRECTORIES
    _platform_match_regex = r'/(%s)/?' % r'|'.join(r'%s' % d for d in PLATFORM_DIRECTORIES)
    _platform_match = re.search(_platform_match_regex, url, re.IGNORECASE)
    platform = _platform_match.groups()[0] if _platform_match else None
    cleaned_url = url.replace('/' + platform, '', 1) if platform is not None else url
    return cleaned_url.rstrip('/'), platform


def split_package_filename(url):
    cleaned_url, package_filename = (url.rsplit('/', 1) if url.endswith(('.tar.bz2', '.json'))
                                     else (url, None))
    return cleaned_url, package_filename


def split_scheme_auth_token(url):
    if not url:
        return None, None, None, None
    cleaned_url, token = split_anaconda_token(url)
    url_parts = urlparse(cleaned_url)
    remainder_url = Url(host=url_parts.host, port=url_parts.port, path=url_parts.path,
                        query=url_parts.query).url
    return remainder_url, url_parts.scheme, url_parts.auth, token


def split_conda_url_easy_parts(url):
    # scheme, auth, token, platform, package_filename, host, port, path, query
    cleaned_url, token = split_anaconda_token(url)
    cleaned_url, platform = split_platform(cleaned_url)
    cleaned_url, package_filename = split_package_filename(cleaned_url)

    # TODO: split out namespace using regex

    url_parts = urlparse(cleaned_url)

    return (url_parts.scheme, url_parts.auth, token, platform, package_filename, url_parts.host,
            url_parts.port, url_parts.path, url_parts.query)


def norm_url_path(path):
    p = path.strip('/')
    return p or '/'


def is_windows_path(value):
    return re.match(r'[a-z]:[/\\]', value, re.IGNORECASE)


@memoize
def get_proxy_username_and_pass(scheme):
    username = input("\n%s proxy username: " % scheme)
    passwd = getpass("Password:")
    return username, passwd


def add_username_and_password(url, username, password):
    url_parts = parse_url(url)._asdict()
    url_parts['auth'] = username + ':' + quote(password, '')
    return Url(**url_parts).url


def maybe_add_auth(url, auth, force=False):
    """add auth if the url doesn't currently have it"""
    if not auth:
        return url
    url_parts = urlparse(url)._asdict()
    if url_parts['auth'] and not force:
        return url
    url_parts['auth'] = auth
    return Url(**url_parts).url


if __name__ == "__main__":
    import doctest
    doctest.testmod()
