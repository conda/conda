# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from getpass import getpass
from logging import getLogger
from os.path import abspath, expanduser
import re
import socket

from .path import split_filename
from .._vendor.auxlib.decorators import memoize
from .._vendor.auxlib.ish import dals
from .._vendor.urllib3.exceptions import LocationParseError
from .._vendor.urllib3.util.url import Url, parse_url
from ..common.compat import on_win

try:  # pragma: py2 no cover
    # Python 3
    from urllib.parse import (quote, quote_plus, unquote, unquote_plus,  # NOQA
                              urlunparse as stdlib_urlparse, urljoin)  # NOQA
    from urllib.request import pathname2url  # NOQA
except ImportError:  # pragma: py3 no cover
    # Python 2
    from urllib import quote, quote_plus, unquote, unquote_plus, pathname2url  # NOQA
    from urlparse import urlunparse as stdlib_urlparse, urljoin  # NOQA


log = getLogger(__name__)


def urlunparse(data):
    return stdlib_urlparse(data) or None


@memoize
def path_to_url(path):
    if not path:
        message = dals("""
        Empty argument to `path_to_url()` not allowed.
        path cannot be '%r'
        """ % path)
        from ..exceptions import CondaValueError
        raise CondaValueError(message)
    if path.startswith('file:/'):
        return path
    path = abspath(expanduser(path))
    url = urljoin('file:', pathname2url(path))
    return url


@memoize
def urlparse(url):
    if on_win and url.startswith('file:'):
        url.replace('\\', '/')
    return parse_url(url)


def url_to_s3_info(url):
    """Convert an s3 url to a tuple of bucket and key.

    Examples:
        >>> url_to_s3_info("s3://bucket-name.bucket/here/is/the/key")
        ('bucket-name.bucket', '/here/is/the/key')
    """
    parsed_url = parse_url(url)
    assert parsed_url.scheme == 's3', "You can only use s3: urls (not %r)" % url
    bucket, key = parsed_url.host, parsed_url.path
    return bucket, key


def is_url(url):
    if not url:
        return False
    try:
        return urlparse(url).scheme is not None
    except LocationParseError:
        return False


def is_ipv4_address(string_ip):
    """
    Examples:
        >>> [is_ipv4_address(ip) for ip in ('8.8.8.8', '192.168.10.10', '255.255.255.255')]
        [True, True, True]
        >>> [is_ipv4_address(ip) for ip in ('8.8.8', '192.168.10.10.20', '256.255.255.255', '::1')]
        [False, False, False, False]
    """
    try:
        socket.inet_aton(string_ip)
    except socket.error:
        return False
    return string_ip.count('.') == 3


def is_ipv6_address(string_ip):
    """
    Examples:
        >>> [is_ipv6_address(ip) for ip in ('::1', '2001:db8:85a3::370:7334', '1234:'*7+'1234')]
        [True, True, True]
        >>> [is_ipv6_address(ip) for ip in ('192.168.10.10', '1234:'*8+'1234')]
        [False, False]
    """
    try:
        inet_pton = socket.inet_pton
    except AttributeError:
        return is_ipv6_address_win_py27(string_ip)
    try:
        inet_pton(socket.AF_INET6, string_ip)
    except socket.error:
        return False
    return True


def is_ipv6_address_win_py27(string_ip):
    """
    Examples:
        >>> [is_ipv6_address_win_py27(ip) for ip in ('::1', '1234:'*7+'1234')]
        [True, True]
        >>> [is_ipv6_address_win_py27(ip) for ip in ('192.168.10.10', '1234:'*8+'1234')]
        [False, False]
    """
    # python 2.7 on windows does not have socket.inet_pton
    return bool(re.match(r"^(((?=.*(::))(?!.*\3.+\3))\3?|[\dA-F]{1,4}:)"
                         r"([\dA-F]{1,4}(\3|:\b)|\2){5}"
                         r"(([\dA-F]{1,4}(\3|:\b|$)|\2){2}|"
                         r"(((2[0-4]|1\d|[1-9])?\d|25[0-5])\.?\b){4})\Z",
                         string_ip,
                         flags=re.DOTALL | re.IGNORECASE))


def is_ip_address(string_ip):
    """
    Examples:
        >>> is_ip_address('192.168.10.10')
        True
        >>> is_ip_address('::1')
        True
        >>> is_ip_address('www.google.com')
        False
    """
    return is_ipv4_address(string_ip) or is_ipv6_address(string_ip)


def join(*args):
    start = '/' if not args[0] or args[0].startswith('/') else ''
    return start + '/'.join(y for y in (x.strip('/') for x in args if x) if y)


join_url = join


def has_scheme(value):
    return re.match(r'[a-z][a-z0-9]{0,11}://', value)


def strip_scheme(url):
    """
    Examples:
        >>> strip_scheme("https://www.conda.io")
        'www.conda.io'
        >>> strip_scheme("s3://some.bucket/plus/a/path.ext")
        'some.bucket/plus/a/path.ext'
    """
    return url.split('://', 1)[-1]


def mask_anaconda_token(url):
    _, token = split_anaconda_token(url)
    return url.replace(token, "<TOKEN>", 1) if token else url


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
    from ..base.constants import PLATFORM_DIRECTORIES
    _platform_match_regex = r'/(%s)/?' % r'|'.join(r'%s' % d for d in PLATFORM_DIRECTORIES)
    _platform_match = re.search(_platform_match_regex, url, re.IGNORECASE)
    platform = _platform_match.groups()[0] if _platform_match else None
    cleaned_url = url.replace('/' + platform, '', 1) if platform is not None else url
    return cleaned_url.rstrip('/'), platform


def has_platform(url):
    from ..base.constants import PLATFORM_DIRECTORIES
    url_no_package_name, _ = split_filename(url)
    if not url_no_package_name:
        return None
    maybe_a_platform = url_no_package_name.rsplit('/', 1)[-1]
    return maybe_a_platform in PLATFORM_DIRECTORIES and maybe_a_platform or None


def _split_package_filename(url):
    cleaned_url, package_filename = (url.rsplit('/', 1) if url.endswith(('.tar.bz2', '.json'))
                                     else (url, None))
    return cleaned_url, package_filename


def split_scheme_auth_token(url):
    """
    Examples:
        >>> split_scheme_auth_token("https://u:p@conda.io/t/x1029384756/more/path")
        ('conda.io/more/path', 'https', 'u:p', 'x1029384756')
        >>> split_scheme_auth_token(None)
        (None, None, None, None)
    """
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
    cleaned_url, package_filename = _split_package_filename(cleaned_url)

    # TODO: split out namespace using regex

    url_parts = urlparse(cleaned_url)

    return (url_parts.scheme, url_parts.auth, token, platform, package_filename, url_parts.host,
            url_parts.port, url_parts.path, url_parts.query)


@memoize
def get_proxy_username_and_pass(scheme):
    username = input("\n%s proxy username: " % scheme)
    passwd = getpass("Password: ")
    return username, passwd


def add_username_and_password(url, username, password):
    url_parts = parse_url(url)._asdict()
    url_parts['auth'] = username + ':' + quote(password, '')
    return Url(**url_parts).url


def maybe_add_auth(url, auth, force=False):
    """Add auth if the url doesn't currently have it.

    By default, does not replace auth if it already exists.  Setting ``force`` to ``True``
    overrides this behavior.

    Examples:
        >>> maybe_add_auth("https://www.conda.io", "user:passwd")
        'https://user:passwd@www.conda.io'
        >>> maybe_add_auth("https://www.conda.io", "")
        'https://www.conda.io'
    """
    if not auth:
        return url
    url_parts = urlparse(url)._asdict()
    if url_parts['auth'] and not force:
        return url
    url_parts['auth'] = auth
    return Url(**url_parts).url


def maybe_unquote(url):
    return unquote_plus(url) if url else url


if __name__ == "__main__":
    import doctest
    doctest.testmod()
