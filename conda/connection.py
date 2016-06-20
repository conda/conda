# (c) 2012-2015 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import cgi
import email
import mimetypes
import os
import platform
import re
import tempfile
from io import BytesIO
from logging import getLogger

import requests

from . import __version__ as VERSION
from .compat import urlparse
from .config import platform as config_platform, ssl_verify, get_proxy_servers
from .utils import gnu_get_libc_version, yaml_bool

RETRIES = 3

log = getLogger(__name__)
stderrlog = getLogger('stderrlog')

# Collect relevant info from OS for reporting purposes (present in User-Agent)
_user_agent = ("conda/{conda_ver} "
               "requests/{requests_ver} "
               "{python}/{py_ver} "
               "{system}/{kernel} {dist}/{ver}")

glibc_ver = gnu_get_libc_version()
if config_platform == 'linux':
    distinfo = platform.linux_distribution()
    dist, ver = distinfo[0], distinfo[1]
elif config_platform == 'osx':
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

# Modified from code in pip/download.py:

# Copyright (c) 2008-2014 The pip developers (see AUTHORS.txt file)
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

class CondaSession(requests.Session):

    timeout = None

    def __init__(self, *args, **kwargs):
        retries = kwargs.pop('retries', RETRIES)

        super(CondaSession, self).__init__(*args, **kwargs)

        proxies = get_proxy_servers()
        if proxies:
            self.proxies = proxies

        # Configure retries
        if retries:
            http_adapter = requests.adapters.HTTPAdapter(max_retries=retries)
            self.mount("http://", http_adapter)
            self.mount("https://", http_adapter)

        # Enable file:// urls
        self.mount("file://", LocalFSAdapter())

        # Enable s3:// urls
        self.mount("s3://", S3Adapter())

        self.headers['User-Agent'] = user_agent

        self.verify = yaml_bool(ssl_verify, ssl_verify)

class S3Adapter(requests.adapters.BaseAdapter):

    def __init__(self):
        super(S3Adapter, self).__init__()
        self._temp_file = None

    def send(self, request, stream=None, timeout=None, verify=None, cert=None,
             proxies=None):

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

        bucket_name, key_string = url_to_S3_info(request.url)

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
            os.remove(self._temp_file)


def url_to_S3_info(url):
    """
    Convert a S3 url to a tuple of bucket and key
    """
    parsed_url = requests.packages.urllib3.util.url.parse_url(url)
    assert parsed_url.scheme == 's3', (
        "You can only use s3: urls (not %r)" % url)
    bucket, key = parsed_url.host, parsed_url.path
    return bucket, key


class LocalFSAdapter(requests.adapters.BaseAdapter):

    def send(self, request, stream=None, timeout=None, verify=None, cert=None,
             proxies=None):
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


_url_drive_re = re.compile('^([a-z])[:|]', re.I)
def url_to_path(url):  # NOQA
    """
    Convert a file: URL to a path.
    """
    assert url.startswith('file:'), (
        "You can only turn file: urls into filenames (not %r)" % url)
    path = url[len('file:'):].lstrip('/')
    path = urlparse.unquote(path)
    if _url_drive_re.match(path):
        path = path[0] + ':' + path[2:]
    elif not path.startswith(r'\\'):
        # if not a Windows UNC path
        path = '/' + path
    return path


def data_callback_factory(variable):
    '''Returns a callback suitable for use by the FTP library. This callback
    will repeatedly save data into the variable provided to this function. This
    variable should be a file-like structure.'''
    def callback(data):
        variable.write(data)
        return

    return callback


class AuthError(Exception):
    '''Denotes an error with authentication.'''
    pass

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

# Taken from urllib3 (actually
# https://github.com/shazow/urllib3/pull/394). Once it is fully upstreamed to
# requests.packages.urllib3 we can just use that.


def unparse_url(U):
    """
    Convert a :class:`.Url` into a url

    The input can be any iterable that gives ['scheme', 'auth', 'host',
    'port', 'path', 'query', 'fragment']. Unused items should be None.

    This function should more or less round-trip with :func:`.parse_url`. The
    returned url may not be exactly the same as the url inputted to
    :func:`.parse_url`, but it should be equivalent by the RFC (e.g., urls
    with a blank port).


    Example: ::

        >>> Url = parse_url('http://google.com/mail/')
        >>> unparse_url(Url)
        'http://google.com/mail/'
        >>> unparse_url(['http', 'username:password', 'host.com', 80,
        ... '/path', 'query', 'fragment'])
        'http://username:password@host.com:80/path?query#fragment'
    """
    scheme, auth, host, port, path, query, fragment = U
    url = ''

    # We use "is not None" we want things to happen with empty strings (or 0 port)
    if scheme is not None:
        url = scheme + '://'
    if auth is not None:
        url += auth + '@'
    if host is not None:
        url += host
    if port is not None:
        url += ':' + str(port)
    if path is not None:
        url += path
    if query is not None:
        url += '?' + query
    if fragment is not None:
        url += '#' + fragment

    return url
