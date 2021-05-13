# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

import os, pickle, re
from urllib.parse import urlparse
from logging import LoggerAdapter, getLogger
from .. import BaseAdapter, Session, Response
from ....common.compat import StringIO

log = getLogger(__name__)
stderrlog = LoggerAdapter(getLogger('conda.stderrlog'), extra=dict(terminator="\n"))

class SecureIDAdapter(BaseAdapter):
    def __init__(self):
        super(SecureIDAdapter, self).__init__()

    def send(self, request, stream=None, timeout=None, verify=None, cert=None, proxies=None):
        session = Session()
        request.url = request.url.replace('rsa', 'https')
        fqdn = urlparse(request.url).hostname
        cookie = getCookie(fqdn)
        session.cookies.update(cookie)
        response = session.get(request.url, verify=False)
        return properResponse(response, request, fqdn)

    def close(self):
        pass

def getCookie(fqdn):
    cookie_file = '%s' % (os.path.sep).join([os.path.expanduser("~"),
                                             '.RSASecureID_login',
                                             fqdn])
    cookie = {}
    if os.path.exists(cookie_file):
        with open(cookie_file, 'rb') as f:
            cookie.update(pickle.load(f))
    else:
        log.warning('RSA Token not available, please sign in using: `rsasecure_login -s %s`' % (fqdn))
    return cookie

def properResponse(response, request, fqdn):
    """ Return non exception causing response when certain conditions arise """
    null_response = Response()
    null_response.raw = StringIO()
    null_response.url = request.url
    null_response.request = request
    null_response.status_code = 204

    if len(response.cookies) == 1:
        return null_response
    elif re.search('RSA SECURID', response.text.upper()):
        log.warning('RSA Token expired. Please sign in using: `rsasecure_login -s %s`' % (fqdn))
        return null_response

    return response
