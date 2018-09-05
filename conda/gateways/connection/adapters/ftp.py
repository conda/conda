# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
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
from __future__ import absolute_import, division, print_function, unicode_literals

from base64 import b64decode
import cgi
import ftplib
from io import BytesIO
from logging import getLogger
import os

from .. import BaseAdapter, Response, dispatch_hook
from ....common.compat import StringIO
from ....common.url import urlparse
from ....exceptions import AuthenticationError

log = getLogger(__name__)


# After: https://stackoverflow.com/a/44073062/3257826
#   And: https://stackoverflow.com/a/35368154/3257826
_old_makepasv = ftplib.FTP.makepasv
def _new_makepasv(self):
    host, port = _old_makepasv(self)
    host = self.sock.getpeername()[0]
    return host, port


ftplib.FTP.makepasv = _new_makepasv


class FTPAdapter(BaseAdapter):
    """A Requests Transport Adapter that handles FTP urls."""
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
        """Sends a PreparedRequest object over FTP. Returns a response object."""
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
        """Dispose of any internal state."""
        # Currently this is a no-op.
        pass

    def list(self, path, request):
        """Executes the FTP LIST command on the given path."""
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
        """Executes the FTP RETR command on the given path."""
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
        """Executes the FTP STOR command on the given path."""

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
        """Executes the FTP NLST command on the given path."""
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
        """Given a PreparedRequest object, reverse the process of adding HTTP
        Basic auth to obtain the username and password. Allows the FTP adapter
        to piggyback on the basic auth notation without changing the control
        flow."""
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
        """Given a PreparedRequest object, split the URL in such a manner as to
        determine the host and the path. This is a separate method to wrap some
        of urlparse's craziness."""
        url = request.url
        parsed = urlparse(url)
        path = parsed.path

        # If there is a slash on the front of the path, chuck it.
        if path[0] == '/':
            path = path[1:]

        host = parsed.hostname
        port = parsed.port or 0

        return (host, port, path)


def data_callback_factory(variable):
    """Returns a callback suitable for use by the FTP library. This callback
    will repeatedly save data into the variable provided to this function. This
    variable should be a file-like structure."""
    def callback(data):
        variable.write(data)
        return

    return callback


def build_text_response(request, data, code):
    """Build a response for textual data."""
    return build_response(request, data, code, 'ascii')


def build_binary_response(request, data, code):
    """Build a response for data whose encoding is unknown."""
    return build_response(request, data, code,  None)


def build_response(request, data, code, encoding):
    """Builds a response object from the data returned by ftplib, using the
    specified encoding."""
    response = Response()

    response.encoding = encoding

    # Fill in some useful fields.
    response.raw = data
    response.url = request.url
    response.request = request
    response.status_code = get_status_code_from_code_response(code)

    # Make sure to seek the file-like raw object back to the start.
    response.raw.seek(0)

    # Run the response hook.
    response = dispatch_hook('response', request.hooks, response)
    return response


def parse_multipart_files(request):
    """Given a prepared reqest, return a file-like object containing the
    original data. This is pretty hacky."""
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


def get_status_code_from_code_response(code):
    """
    The idea is to handle complicated code response (even multi lines).
    We get the status code in two ways:
    - extracting the code from the last valid line in the response
    - getting it from the 3 first digits in the code
    After a comparison between the two values,
    we can safely set the code or raise a warning.
    Examples:
        - get_status_code_from_code_response('200 Welcome') == 200
        - multi_line_code = '226-File successfully transferred\n226 0.000 seconds'
          get_status_code_from_code_response(multi_line_code) == 226
        - multi_line_with_code_conflicts = '200-File successfully transferred\n226 0.000 seconds'
          get_status_code_from_code_response(multi_line_with_code_conflicts) == 226
    For more detail see RFC 959, page 36, on multi-line responses:
        https://www.ietf.org/rfc/rfc959.txt
        "Thus the format for multi-line replies is that the first line
         will begin with the exact required reply code, followed
         immediately by a Hyphen, "-" (also known as Minus), followed by
         text.  The last line will begin with the same code, followed
         immediately by Space <SP>, optionally some text, and the Telnet
         end-of-line code."
    """
    last_valid_line_from_code = [line for line in code.split('\n') if line][-1]
    status_code_from_last_line = int(last_valid_line_from_code.split()[0])
    status_code_from_first_digits = int(code[:3])
    if status_code_from_last_line != status_code_from_first_digits:
        log.warning(
            'FTP response status code seems to be inconsistent.\n'
            'Code received: %s, extracted: %s and %s',
            code,
            status_code_from_last_line,
            status_code_from_first_digits
        )
    return status_code_from_last_line
