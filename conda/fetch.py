# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.


import os
import bz2
import json
import hashlib
import urllib2
import logging
from os.path import join

import config

#START proxy support

#1. get proxies if needed. a proxy for each  protocol
#2. handle authentication
#basic, digest, and nltm (windows) authentications should be handled.
#3. handle any protocol
#typically http, https, ftp

#1. get the proxies list
proxies_dict=urllib2.getproxies()
# urllib can only get proxies on windows and mac. so on linux or if the user
# wants to specify the proxy there has to be a way to do that. TODO get proxies
#from condarc and overrwrite any system proxies
#the proxies are in a dict {'http':'http://proxy:8080'}
#protocol:proxyserver

#2. handle authentication

proxypwdmgr=urllib2.HTTPPasswordMgrWithDefaultRealm()

def get_userandpass(proxytype='',realm=''):
    """a function to get username and password from terminal.
    can be replaced with anything like some gui"""
    uname=raw_input(proxytype+' proxy username:')
    import getpass
    pword=getpass.getpass()
    return uname,pword


#a procedure that needs to be executed with changes to handlers
def installopener():
    opener = urllib2.build_opener(urllib2.ProxyHandler(proxies_dict)
                                ,urllib2.ProxyBasicAuthHandler(proxypwdmgr)
                                ,urllib2.ProxyDigestAuthHandler(proxypwdmgr)
#digest auth may not work with all proxies http://bugs.python.org/issue16095
                                )#could add windows/nltm authentication here
    urllib2.install_opener(opener)
    return

import urlparse
firstconnection=True
#i made this func so i wouldn't alter the original code much
def connectionhandled_urlopen(url):
    """handles aspects of establishing the connection with the remote"""

    try: return urllib2.urlopen(url)
    
    except urllib2.HTTPError as HTTPErrorinst:
        if HTTPErrorinst.code==407 or 401:#proxy authentication error
            #...(need to auth) or supplied creds failed
            if HTTPErrorinst.code==401: log.debug('proxy authentication failed')
            #authenticate and retry
            uname,pword=get_userandpass()
            #assign same user+pwd to all protocols (a reasonable assumption) to
            #decrease user input. otherwise you'd need to assign a user/pwd to
            #each proxy type
            if firstconnection==True:
                for aprotocol, aproxy in proxies_dict.iteritems():
                    proxypwdmgr.add_password(None,aproxy,uname,pword)
                firstconnection==False
            else:#...assign a uname pwd for the specific protocol proxy type
                assert(firstconnection==False)
                protocol=urlparse.urlparse(url).scheme
                proxypwdmgr.add_password(None,proxies_dict[protocol],uname,pword)
            installopener()
            return connectionhandled_urlopen(url)#i'm uncomfortable with this
			#but i just want to exec to start from the top again

    except: raise #returns anything unhandled here to the caller

#END proxy support
    
log = logging.getLogger(__name__)

retries = 3


def fetch_repodata(url):
    for x in range(retries):
        for fn in 'repodata.json.bz2', 'repodata.json':
            try:
                fi = connectionhandled_urlopen(url+fn)#urllib2.urlopen(url + fn)
                        
                log.debug("fetched: %s [%s] ..." % (fn, url))
                data = fi.read()
                fi.close()
                if fn.endswith('.bz2'):
                    data = bz2.decompress(data)
                return json.loads(data)

            except IOError:
                log.debug('download failed try: %d' % x)

    raise RuntimeError("failed to fetch repodata from %r" % url)


def fetch_index(channel_urls):
    index = {}
    for url in reversed(channel_urls):
        repodata = fetch_repodata(url)
        new_index = repodata['packages']
        for info in new_index.itervalues():
            info['channel'] = url
        index.update(new_index)
    return index


def fetch_pkg(info, progress=None, dst_dir=config.pkgs_dir):
    '''
    fetch a package `fn` from `url` and store it into `dst_dir`
    '''
    fn = '%(name)s-%(version)s-%(build)s.tar.bz2' % info
    url = info['channel'] + fn
    path = join(dst_dir, fn)
    pp = path + '.part'

    for x in range(retries):
        try:
            fi = connectionhandled_urlopen(url)#urllib2.urlopen(url)
        except IOError:
            log.debug("Attempt %d failed at urlopen" % x)
            continue
        log.debug("Fetching: %s" % url)
        n = 0
        h = hashlib.new('md5')
        if progress:
            progress.widgets[0] = fn
            progress.maxval = info['size']
            progress.start()

        need_retry = False
        try:
            fo = open(pp, 'wb')
        except IOError:
            raise RuntimeError("Could not open %r for writing.  "
                         "Permissions problem or missing directory?" % pp)
        while True:
            try:
                chunk = fi.read(16384)
            except IOError:
                log.debug("Attempt %d failed at read" % x)
                need_retry = True
                break
            if not chunk:
                break
            try:
                fo.write(chunk)
            except IOError:
                raise RuntimeError("Failed to write to %r." % pp)
            h.update(chunk)
            n += len(chunk)
            if progress:
                progress.update(n)

        fo.close()
        if need_retry:
            continue

        fi.close()
        if progress:
            progress.finish()
        if h.hexdigest() != info['md5']:
            raise RuntimeError("MD5 sums mismatch for download: %s" % fn)
        try:
            os.rename(pp, path)
        except OSError:
            raise RuntimeError("Could not rename %r to %r." % (pp, path))
        return

    raise RuntimeError("Could not locate file '%s' on any repository" % fn)
