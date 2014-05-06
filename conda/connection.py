# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

from logging import getLogger
import re
import mimetypes
import os
import email

from conda.compat import urlparse
from conda.config import get_proxy_servers

import requests

RETRIES = 3

log = getLogger(__name__)

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

        self.proxies = get_proxy_servers()

        # Configure retries
        if retries:
            http_adapter = requests.adapters.HTTPAdapter(max_retries=retries)
            self.mount("http://", http_adapter)
            self.mount("https://", http_adapter)

        # Enable file:// urls
        self.mount("file://", LocalFSAdapter())


class LocalFSResponse(object):

    def __init__(self, fileobj):
        self.fileobj = fileobj

    def __getattr__(self, name):
        return getattr(self.fileobj, name)

    def read(self, amt=None, decode_content=None, cache_content=False):
        return self.fileobj.read(amt)

    # Insert Hacks to Make Cookie Jar work w/ Requests
    @property
    def _original_response(self):
        class FakeMessage(object):
            def getheaders(self, header):
                return []

            def get_all(self, header, default):
                return []

        class FakeResponse(object):
            @property
            def msg(self):
                return FakeMessage()

        return FakeResponse()


class LocalFSAdapter(requests.adapters.BaseAdapter):

    def send(self, request, stream=None, timeout=None, verify=None, cert=None,
             proxies=None):
        parsed_url = urlparse.urlparse(request.url)

        # We only work for requests with a host of localhost
        if parsed_url.netloc.lower() != "localhost":
            raise requests.exceptions.InvalidURL(
                "Invalid URL %r: Only localhost is allowed" %
                request.url
            )

        real_url = urlparse.urlunparse(parsed_url[:1] + ("",) + parsed_url[2:])
        pathname = url_to_path(real_url)

        resp = requests.models.Response()
        resp.status_code = 200
        resp.url = real_url

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

            resp.raw = LocalFSResponse(open(pathname, "rb"))
            resp.close = resp.raw.close

        return resp

    def close(self):
        pass

def url_to_path(url):
    """
    Convert a file: URL to a path.
    """
    from conda.compat import urlparse
    assert url.startswith('file:'), (
        "You can only turn file: urls into filenames (not %r)" % url)
    path = url[len('file:'):].lstrip('/')
    path = urlparse.unquote(path)
    if _url_drive_re.match(path):
        path = path[0] + ':' + path[2:]
    else:
        path = '/' + path
    return path

_url_drive_re = re.compile('^([a-z])[:|]', re.I)
