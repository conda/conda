# (c) 2012-2015 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
import platform

from requests import Session, __version__ as REQUESTS_VERSION
from requests.adapters import BaseAdapter, HTTPAdapter
from requests.auth import AuthBase, _basic_auth_str
from requests.cookies import extract_cookies_to_jar
from requests.utils import get_auth_from_url, get_netrc_auth

from . import __version__ as VERSION
from ._vendor.auxlib.ish import dals
from .base.constants import CONDA_HOMEPAGE_URL
from .base.context import context
from .common.compat import iteritems
from .common.url import (add_username_and_password, get_proxy_username_and_pass,
                         split_anaconda_token, urlparse)
from .exceptions import ProxyError
from .gateways.adapters.ftp import FTPAdapter
from .gateways.adapters.localfs import LocalFSAdapter
from .gateways.adapters.s3 import S3Adapter
from .gateways.anaconda_client import read_binstar_tokens
from .utils import gnu_get_libc_version

RETRIES = 3

log = getLogger(__name__)

# Collect relevant info from OS for reporting purposes (present in User-Agent)
_user_agent = ("conda/{conda_ver} "
               "requests/{requests_ver} "
               "{python}/{py_ver} "
               "{system}/{kernel} {dist}/{ver}")

glibc_ver = gnu_get_libc_version()
if context.platform == 'linux':
    distinfo = platform.linux_distribution()
    dist, ver = distinfo[0], distinfo[1]
elif context.platform == 'osx':
    dist = 'OSX'
    ver = platform.mac_ver()[0]
else:
    dist = platform.system()
    ver = platform.version()

user_agent = _user_agent.format(conda_ver=VERSION,
                                requests_ver=REQUESTS_VERSION,
                                python=platform.python_implementation(),
                                py_ver=platform.python_version(),
                                system=platform.system(), kernel=platform.release(),
                                dist=dist, ver=ver)
if glibc_ver:
    user_agent += " glibc/{}".format(glibc_ver)


class EnforceUnusedAdapter(BaseAdapter):

    def send(self, request, *args, **kwargs):
        message = dals("""
        EnforceUnusedAdapter called with url %s
        This command is using a remote connection in offline mode.
        """ % request.url)
        raise RuntimeError(message)

    def close(self):
        raise NotImplementedError()


class CondaSession(Session):

    def __init__(self, *args, **kwargs):
        super(CondaSession, self).__init__(*args, **kwargs)

        self.auth = CondaHttpAuth()  # TODO: should this just be for certain protocol adapters?

        proxies = context.proxy_servers
        if proxies:
            self.proxies = proxies

        if context.offline:
            unused_adapter = EnforceUnusedAdapter()
            self.mount("http://", unused_adapter)
            self.mount("https://", unused_adapter)
            self.mount("ftp://", unused_adapter)
            self.mount("s3://", unused_adapter)

        else:
            # Configure retries
            http_adapter = HTTPAdapter(max_retries=context.remote_max_retries)
            self.mount("http://", http_adapter)
            self.mount("https://", http_adapter)
            self.mount("ftp://", FTPAdapter())
            self.mount("s3://", S3Adapter())

        self.mount("file://", LocalFSAdapter())

        self.headers['User-Agent'] = user_agent

        self.verify = context.ssl_verify

        if context.client_ssl_cert_key:
            self.cert = (context.client_ssl_cert, context.client_ssl_cert_key)
        elif context.client_ssl_cert:
            self.cert = context.client_ssl_cert


class CondaHttpAuth(AuthBase):
    # TODO: make this class thread-safe by adding some of the requests.auth.HTTPDigestAuth() code

    def __call__(self, request):
        request.url = CondaHttpAuth.add_binstar_token(request.url)
        self._apply_basic_auth(request)
        request.register_hook('response', self.handle_407)
        return request

    @staticmethod
    def _apply_basic_auth(request):
        # this logic duplicated from Session.prepare_request and PreparedRequest.prepare_auth
        url_auth = get_auth_from_url(request.url)
        auth = url_auth if any(url_auth) else None

        if auth is None:
            # look for auth information in a .netrc file
            auth = get_netrc_auth(request.url)

        if isinstance(auth, tuple) and len(auth) == 2:
            request.headers['Authorization'] = _basic_auth_str(*auth)

        return request

    @staticmethod
    def add_binstar_token(url):
        clean_url, token = split_anaconda_token(url)
        if not token:
            for binstar_url, token in iteritems(read_binstar_tokens()):
                if clean_url.startswith(binstar_url):
                    log.debug("Adding anaconda token for url <%s>", clean_url)
                    from conda.models.channel import Channel
                    channel = Channel(clean_url)
                    channel.token = token
                    return channel.url(with_credentials=True)
        return url

    @staticmethod
    def handle_407(response, **kwargs):
        """
        Prompts the user for the proxy username and password and modifies the
        proxy in the session object to include it.

        This method is modeled after
          * requests.auth.HTTPDigestAuth.handle_401()
          * requests.auth.HTTPProxyAuth
          * the previous conda.fetch.handle_proxy_407()

        It both adds 'username:password' to the proxy URL, as well as adding a
        'Proxy-Authorization' header.  If any of this is incorrect, please file an issue.

        """
        # kwargs = {'verify': True, 'cert': None, 'proxies': OrderedDict(), 'stream': False,
        #           'timeout': (3.05, 60)}

        if response.status_code != 407:
            return response

        # Consume content and release the original connection
        # to allow our new request to reuse the same one.
        response.content
        response.close()

        proxies = kwargs.pop('proxies')

        proxy_scheme = urlparse(response.url).scheme
        if proxy_scheme not in proxies:
            raise ProxyError(dals("""
            Could not find a proxy for %r. See
            %s/docs/html#configure-conda-for-use-behind-a-proxy-server
            for more information on how to configure proxies.
            """ % (proxy_scheme, CONDA_HOMEPAGE_URL)))

        # fix-up proxy_url with username & password
        proxy_url = proxies[proxy_scheme]
        username, password = get_proxy_username_and_pass(proxy_scheme)
        proxy_url = add_username_and_password(proxy_url, username, password)
        proxy_authorization_header = _basic_auth_str(username, password)
        proxies[proxy_scheme] = proxy_url
        kwargs['proxies'] = proxies

        prep = response.request.copy()
        extract_cookies_to_jar(prep._cookies, response.request, response.raw)
        prep.prepare_cookies(prep._cookies)
        prep.headers['Proxy-Authorization'] = proxy_authorization_header

        _response = response.connection.send(prep, **kwargs)
        _response.history.append(response)
        _response.request = prep

        return _response
