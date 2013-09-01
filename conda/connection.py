# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

from logging import getLogger

from conda.compat import PY3
from conda.compat import iteritems, input
from conda.config import get_proxy_servers

if PY3:
    # Python 3.x
    import urllib.request as urllib2
    from urllib import parse as urlparse
else:
    # Python 2.x
    import urllib2
    import urlparse


log = getLogger(__name__)

# 1. get proxies if needed. a proxy for each  protocol
# 2. handle authentication
# basic, digest, and nltm (windows) authentications should be handled.
# 3. handle any protocol
# typically http, https, ftp

# 1. get the proxies list
proxies_dict=urllib2.getproxies()
# urllib can only get proxies on windows and mac. so on linux or if the user
# wants to specify the proxy there has to be a way to do that. TODO get proxies
# from condarc and overrwrite any system proxies
# the proxies are in a dict {'http':'http://proxy:8080'}
# protocol:proxyserver

if get_proxy_servers():
    proxies_dict = get_proxy_servers()

#2. handle authentication

proxypwdmgr = urllib2.HTTPPasswordMgrWithDefaultRealm()


def get_userandpass(proxytype='',realm=''):
    """a function to get username and password from terminal.
    can be replaced with anything like some gui"""
    import getpass

    uname = input(proxytype + ' proxy username:')
    pword = getpass.getpass()
    return uname, pword


# a procedure that needs to be executed with changes to handlers
def installopener():
    opener = urllib2.build_opener(
        urllib2.ProxyHandler(proxies_dict),
        urllib2.ProxyBasicAuthHandler(proxypwdmgr),
        urllib2.ProxyDigestAuthHandler(proxypwdmgr),
        urllib2.HTTPHandler,
    )
    # digest auth may not work with all proxies
    # http://bugs.python.org/issue16095
    # could add windows/nltm authentication here
    #opener=urllib2.build_opener(urllib2.ProxyHandler(proxies_dict), urllib2.HTTPHandler)

    urllib2.install_opener(opener)


firstconnection = True
#i made this func so i wouldn't alter the original code much
def connectionhandled_urlopen(request):
    """handles aspects of establishing the connection with the remote"""

    installopener()

    if isinstance(request, (str, unicode)):
        request = urllib2.Request(request)

    try:
        return urllib2.urlopen(request)

    except urllib2.HTTPError as HTTPErrorinst:
        if HTTPErrorinst.code in (407, 401):
            # proxy authentication error
            # ...(need to auth) or supplied creds failed
            if HTTPErrorinst.code == 401:
                log.debug('proxy authentication failed')
            #authenticate and retry
            uname, pword = get_userandpass()
            #assign same user+pwd to all protocols (a reasonable assumption) to
            #decrease user input. otherwise you'd need to assign a user/pwd to
            #each proxy type
            if firstconnection == True:
                for aprotocol, aproxy in iteritems(proxies_dict):
                    proxypwdmgr.add_password(None, aproxy, uname, pword)
                firstconnection == False
            else: #...assign a uname pwd for the specific protocol proxy type
                assert(firstconnection == False)
                protocol = urlparse.urlparse(request.get_full_url()).scheme
                proxypwdmgr.add_password(None, proxies_dict[protocol],
                                         uname, pword)
            installopener()
            # i'm uncomfortable with this
            # but i just want to exec to start from the top again
            return connectionhandled_urlopen(request)
        raise

    except:
        raise
