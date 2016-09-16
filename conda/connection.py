# (c) 2012-2015 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import absolute_import, division, print_function

import cgi
import email
import ftplib
import mimetypes
import os
import platform
import requests
import tempfile
from base64 import b64decode
from io import BytesIO
from logging import getLogger
from requests.adapters import HTTPAdapter
from requests.auth import AuthBase
from requests.packages.urllib3.util import Url

from . import __version__ as VERSION
from .base.constants import DEFAULT_CHANNEL_ALIAS
from .base.context import context
from .common.disk import rm_rf
from .common.url import url_to_path, url_to_s3_info, urlparse
from .compat import StringIO
from .exceptions import AuthenticationError
from .models.channel import split_token
from .utils import gnu_get_libc_version

RETRIES = 3

log = getLogger(__name__)
stderrlog = getLogger('stderrlog')

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
                                requests_ver=requests.__version__,
                                python=platform.python_implementation(),
                                py_ver=platform.python_version(),
                                system=platform.system(), kernel=platform.release(),
                                dist=dist, ver=ver)
if glibc_ver:
    user_agent += " glibc/{}".format(glibc_ver)


class BinstarAuth(AuthBase):

    def __call__(self, request):
        request.url = BinstarAuth.add_binstar_token(request.url)
        return request

    @staticmethod
    def add_binstar_token(url):
        if not context.add_anaconda_token or not BinstarAuth.is_binstar_url_needing_token(url):
            return url
        token = context.anaconda_token or BinstarAuth.get_binstar_token(url)
        if not token:
            return url
        log.debug("Adding binstar token to url %s", url)
        u = urlparse(url)
        path = u.path if u.path.startswith('/t/') else "/t/%s/%s" % (token, u.path.lstrip('/'))
        return Url(u.scheme, u.auth, u.host, u.port, path, u.query).url

    @staticmethod
    def get_binstar_token(url):
        try:
            log.debug("Attempting to binstar collect token for url %s", url)
            try:
                from binstar_client.utils import get_config, load_token
            except ImportError:
                log.debug("Could not import binstar_client.")
                return None

            binstar_default_url = 'https://api.anaconda.org'
            url_parts = urlparse(url)
            base_url = '%s://%s' % (url_parts.scheme, url_parts.netloc)
            if DEFAULT_CHANNEL_ALIAS.startswith(base_url):
                base_url = binstar_default_url

            config = get_config()  # remote_site is site name, not url
            url_from_bs_config = config.get('url', base_url)
            token = load_token(url_from_bs_config)

            return token
        except Exception as e:
            log.warn("Warning: could not capture token from anaconda-client (%r)", e)
            return None

    @staticmethod
    def is_binstar_url_needing_token(url):
        urlparts = urlparse(url)
        token, path = split_token(urlparts.path)
        if token:  # url already has token
            return False
        return (urlparts.scheme in ('http', 'https') and
                any(urlparts.hostname.endswith(bh) for bh in context.binstar_hosts))


class CondaSession(requests.Session):

    timeout = None

    def __init__(self, *args, **kwargs):
        retries = kwargs.pop('retries', RETRIES)

        super(CondaSession, self).__init__(*args, **kwargs)

        self.auth = BinstarAuth()

        proxies = context.proxy_servers
        if proxies:
            self.proxies = proxies

        # Configure retries
        if retries:
            http_adapter = HTTPAdapter(max_retries=retries)
            self.mount("http://", http_adapter)
            self.mount("https://", http_adapter)

        # Enable file:// urls
        self.mount("file://", LocalFSAdapter())

        # Enable ftp:// urls
        self.mount("ftp://", FTPAdapter())

        # Enable s3:// urls
        self.mount("s3://", S3Adapter())

        self.headers['User-Agent'] = user_agent

        self.verify = context.ssl_verify

        if context.client_cert_key:
            self.cert = (context.client_cert, context.client_cert_key)
        elif context.client_cert:
            self.cert = context.client_cert


class S3Adapter(requests.adapters.BaseAdapter):

    def __init__(self):
        super(S3Adapter, self).__init__()
        self._temp_file = None

    def send(self, request, stream=None, timeout=None, verify=None, cert=None, proxies=None):

        resp = requests.models.Response()
        resp.status_code = 200
        resp.url = request.url

        try:
            import boto

            # silly patch for AWS because
            # TODO: remove or change to warning once boto >2.39.0 is released
            # https://github.com/boto/boto/issues/2617
            from boto.pyami.config import Config, ConfigParser

            def get(self, section, name, default=None, **kw):
                try:
                    val = ConfigParser.get(self, section, name, **kw)
                except:
                    val = default
                return val

            Config.get = get

        except ImportError:
            stderrlog.info('\nError: boto is required for S3 channels. '
                           'Please install it with `conda install boto`\n'
                           'Make sure to run `source deactivate` if you '
                           'are in a conda environment.\n')
            resp.status_code = 404
            return resp

        conn = boto.connect_s3()

        bucket_name, key_string = url_to_s3_info(request.url)

        # Get the bucket without validation that it exists and that we have
        # permissions to list its contents.
        bucket = conn.get_bucket(bucket_name, validate=False)

        try:
            key = bucket.get_key(key_string)
        except boto.exception.S3ResponseError as exc:
            # This exception will occur if the bucket does not exist or if the
            # user does not have permission to list its contents.
            resp.status_code = 404
            resp.raw = exc
            return resp

        if key and key.exists:
            modified = key.last_modified
            content_type = key.content_type or "text/plain"
            resp.headers = requests.structures.CaseInsensitiveDict({
                "Content-Type": content_type,
                "Content-Length": key.size,
                "Last-Modified": modified,
                })

            _, self._temp_file = tempfile.mkstemp()
            key.get_contents_to_filename(self._temp_file)
            f = open(self._temp_file, 'rb')
            resp.raw = f
            resp.close = resp.raw.close
        else:
            resp.status_code = 404

        return resp

    def close(self):
        if self._temp_file:
            rm_rf(self._temp_file)


class LocalFSAdapter(requests.adapters.BaseAdapter):

    def send(self, request, stream=None, timeout=None, verify=None, cert=None, proxies=None):
        pathname = url_to_path(request.url)

        resp = requests.models.Response()
        resp.status_code = 200
        resp.url = request.url

        try:
            stats = os.stat(pathname)
        except OSError as exc:
            resp.status_code = 404
            resp.raw = exc
        else:
            modified = email.utils.formatdate(stats.st_mtime, usegmt=True)
            content_type = mimetypes.guess_type(pathname)[0] or "text/plain"
            resp.headers = requests.structures.CaseInsensitiveDict({
                "Content-Type": content_type,
                "Content-Length": stats.st_size,
                "Last-Modified": modified,
            })

            resp.raw = open(pathname, "rb")
            resp.close = resp.raw.close

        return resp

    def close(self):
        pass


# Taken from requests-ftp
# (https://github.com/Lukasa/requests-ftp/blob/master/requests_ftp/ftp.py)

# Copyright 2012 Cory Benfield

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

class FTPAdapter(requests.adapters.BaseAdapter):
    '''A Requests Transport Adapter that handles FTP urls.'''
    def __init__(self):
        super(FTPAdapter, self).__init__()

        # Build a dictionary keyed off the methods we support in upper case.
        # The values of this dictionary should be the functions we use to
        # send the specific queries.
        self.func_table = {'LIST': self.list,
                           'RETR': self.retr,
                           'STOR': self.stor,
                           'NLST': self.nlst,
                           'GET': self.retr}

    def send(self, request, **kwargs):
        '''Sends a PreparedRequest object over FTP. Returns a response object.
        '''
        # Get the authentication from the prepared request, if any.
        auth = self.get_username_password_from_header(request)

        # Next, get the host and the path.
        host, port, path = self.get_host_and_path_from_url(request)

        # Sort out the timeout.
        timeout = kwargs.get('timeout', None)
        if not isinstance(timeout, int):
            # https://github.com/conda/conda/pull/3392
            timeout = 10

        # Establish the connection and login if needed.
        self.conn = ftplib.FTP()
        self.conn.connect(host, port, timeout)

        if auth is not None:
            self.conn.login(auth[0], auth[1])
        else:
            self.conn.login()

        # Get the method and attempt to find the function to call.
        resp = self.func_table[request.method](path, request)

        # Return the response.
        return resp

    def close(self):
        '''Dispose of any internal state.'''
        # Currently this is a no-op.
        pass

    def list(self, path, request):
        '''Executes the FTP LIST command on the given path.'''
        data = StringIO()

        # To ensure the StringIO gets cleaned up, we need to alias its close
        # method to the release_conn() method. This is a dirty hack, but there
        # you go.
        data.release_conn = data.close

        self.conn.cwd(path)
        code = self.conn.retrbinary('LIST', data_callback_factory(data))

        # When that call has finished executing, we'll have all our data.
        response = build_text_response(request, data, code)

        # Close the connection.
        self.conn.close()

        return response

    def retr(self, path, request):
        '''Executes the FTP RETR command on the given path.'''
        data = BytesIO()

        # To ensure the BytesIO gets cleaned up, we need to alias its close
        # method. See self.list().
        data.release_conn = data.close

        code = self.conn.retrbinary('RETR ' + path, data_callback_factory(data))

        response = build_binary_response(request, data, code)

        # Close the connection.
        self.conn.close()

        return response

    def stor(self, path, request):
        '''Executes the FTP STOR command on the given path.'''

        # First, get the file handle. We assume (bravely)
        # that there is only one file to be sent to a given URL. We also
        # assume that the filename is sent as part of the URL, not as part of
        # the files argument. Both of these assumptions are rarely correct,
        # but they are easy.
        data = parse_multipart_files(request)

        # Split into the path and the filename.
        path, filename = os.path.split(path)

        # Switch directories and upload the data.
        self.conn.cwd(path)
        code = self.conn.storbinary('STOR ' + filename, data)

        # Close the connection and build the response.
        self.conn.close()

        response = build_binary_response(request, BytesIO(), code)

        return response

    def nlst(self, path, request):
        '''Executes the FTP NLST command on the given path.'''
        data = StringIO()

        # Alias the close method.
        data.release_conn = data.close

        self.conn.cwd(path)
        code = self.conn.retrbinary('NLST', data_callback_factory(data))

        # When that call has finished executing, we'll have all our data.
        response = build_text_response(request, data, code)

        # Close the connection.
        self.conn.close()

        return response

    def get_username_password_from_header(self, request):
        '''Given a PreparedRequest object, reverse the process of adding HTTP
        Basic auth to obtain the username and password. Allows the FTP adapter
        to piggyback on the basic auth notation without changing the control
        flow.'''
        auth_header = request.headers.get('Authorization')

        if auth_header:
            # The basic auth header is of the form 'Basic xyz'. We want the
            # second part. Check that we have the right kind of auth though.
            encoded_components = auth_header.split()[:2]
            if encoded_components[0] != 'Basic':
                raise AuthenticationError('Invalid form of Authentication used.')
            else:
                encoded = encoded_components[1]

            # Decode the base64 encoded string.
            decoded = b64decode(encoded)

            # The string is of the form 'username:password'. Split on the
            # colon.
            components = decoded.split(':')
            username = components[0]
            password = components[1]
            return (username, password)
        else:
            # No auth header. Return None.
            return None

    def get_host_and_path_from_url(self, request):
        '''Given a PreparedRequest object, split the URL in such a manner as to
        determine the host and the path. This is a separate method to wrap some
        of urlparse's craziness.'''
        url = request.url
        # scheme, netloc, path, params, query, fragment = urlparse(url)
        parsed = urlparse(url)
        path = parsed.path

        # If there is a slash on the front of the path, chuck it.
        if path[0] == '/':
            path = path[1:]

        host = parsed.hostname
        port = parsed.port or 0

        return (host, port, path)


def data_callback_factory(variable):
    '''Returns a callback suitable for use by the FTP library. This callback
    will repeatedly save data into the variable provided to this function. This
    variable should be a file-like structure.'''
    def callback(data):
        variable.write(data)
        return

    return callback


def build_text_response(request, data, code):
    '''Build a response for textual data.'''
    return build_response(request, data, code, 'ascii')


def build_binary_response(request, data, code):
    '''Build a response for data whose encoding is unknown.'''
    return build_response(request, data, code,  None)


def build_response(request, data, code, encoding):
    '''Builds a response object from the data returned by ftplib, using the
    specified encoding.'''
    response = requests.Response()

    response.encoding = encoding

    # Fill in some useful fields.
    response.raw = data
    response.url = request.url
    response.request = request
    response.status_code = int(code.split()[0])

    # Make sure to seek the file-like raw object back to the start.
    response.raw.seek(0)

    # Run the response hook.
    response = requests.hooks.dispatch_hook('response', request.hooks, response)
    return response


def parse_multipart_files(request):
    '''Given a prepared reqest, return a file-like object containing the
    original data. This is pretty hacky.'''
    # Start by grabbing the pdict.
    _, pdict = cgi.parse_header(request.headers['Content-Type'])

    # Now, wrap the multipart data in a BytesIO buffer. This is annoying.
    buf = BytesIO()
    buf.write(request.body)
    buf.seek(0)

    # Parse the data. Simply take the first file.
    data = cgi.parse_multipart(buf, pdict)
    _, filedata = data.popitem()
    buf.close()

    # Get a BytesIO now, and write the file into it.
    buf = BytesIO()
    buf.write(''.join(filedata))
    buf.seek(0)

    return buf
