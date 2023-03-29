# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

import os
import pickle
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
        request.url = request.url.replace('rsa://', 'https://')
        fqdn = urlparse(request.url).hostname
        cookie = getCookie(fqdn)
        session.cookies.update(cookie)
        response = session.get(request.url,
                               stream=stream,
                               timeout=1,
                               verify=verify,
                               cert=cert,
                               proxies=proxies)
        response.request = request
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

    return cookie

def properResponse(response, request, fqdn):
    """ Return non exception causing response when certain conditions arise """
    # RSA sites are Text, while Conda is application/*
    if 'application' not in response.headers['Content-Type']:
        null_response = Response()
        null_response.raw = StringIO()
        null_response.url = request.url
        null_response.request = request
        null_response.status_code = 204
        log.warning('RSA Token expired')
        return null_response

    return response
