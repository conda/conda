# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

import getpass
import hashlib
import os
import shutil
import sys
import tempfile
import warnings
from functools import wraps
from logging import getLogger
from os.path import dirname, basename, join

import requests

from conda.common.compat import input, urllib_quote
from conda.common.lock import Locked
from conda.common.utils import memoized
from conda.connection import unparse_url, CondaSession, RETRIES

log = getLogger(__name__)
dotlog = getLogger('dotupdate')
stdoutlog = getLogger('stdoutlog')
stderrlog = getLogger('stderrlog')


def add_http_value_to_dict(resp, http_key, d, dict_key):
    value = resp.headers.get(http_key)
    if value:
        d[dict_key] = value

# We need a decorator so that the dot gets printed *after* the repodata is fetched
class dotlog_on_return(object):
    def __init__(self, msg):
        self.msg = msg

    def __call__(self, f):
        @wraps(f)
        def func(*args, **kwargs):
            res = f(*args, **kwargs)
            dotlog.debug("%s args %s kwargs %s" % (self.msg, args, kwargs))
            return res
        return func


def handle_proxy_407(url, session):
    """
    Prompts the user for the proxy username and password and modifies the
    proxy in the session object to include it.
    """
    # We could also use HTTPProxyAuth, but this does not work with https
    # proxies (see https://github.com/kennethreitz/requests/issues/2061).
    scheme = requests.packages.urllib3.util.url.parse_url(url).scheme
    if scheme not in session.proxies:
        sys.exit("""Could not find a proxy for %r. See
http://conda.pydata.org/docs/config.html#configure-conda-for-use-behind-a-proxy-server
for more information on how to configure proxies.""" % scheme)
    username, passwd = get_proxy_username_and_pass(scheme)
    session.proxies[scheme] = add_username_and_pass_to_url(
                           session.proxies[scheme], username, passwd)


def add_username_and_pass_to_url(url, username, passwd):
    urlparts = list(requests.packages.urllib3.util.url.parse_url(url))
    passwd = urllib_quote(passwd, '')
    urlparts[1] = username + ':' + passwd
    return unparse_url(urlparts)


@memoized
def get_proxy_username_and_pass(scheme):
    username = input("\n%s proxy username: " % scheme)
    passwd = getpass.getpass("Password:")
    return username, passwd


def download(url, dst_path, session=None, md5=None, urlstxt=False,
             retries=None, ssl_verify=True):
    pp = dst_path + '.part'
    dst_dir = dirname(dst_path)
    session = session or CondaSession()

    if not config.ssl_verify:
        try:
            from requests.packages.urllib3.connectionpool import InsecureRequestWarning
        except ImportError:
            pass
        else:
            warnings.simplefilter('ignore', InsecureRequestWarning)

    if retries is None:
        retries = RETRIES
    with Locked(dst_dir):
        try:
            resp = session.get(url, stream=True, proxies=session.proxies)
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 407: # Proxy Authentication Required
                handle_proxy_407(url, session)
                # Try again
                return download(url, dst_path, session=session, md5=md5,
                                urlstxt=urlstxt, retries=retries, ssl_verify=ssl_verify)
            msg = "HTTPError: %s: %s\n" % (e, url)
            log.debug(msg)
            raise RuntimeError(msg)

        except requests.exceptions.ConnectionError as e:
            # requests isn't so nice here. For whatever reason, https gives
            # this error and http gives the above error. Also, there is no
            # status_code attribute here.  We have to just check if it looks
            # like 407.
            # See: https://github.com/kennethreitz/requests/issues/2061.
            if "407" in str(e): # Proxy Authentication Required
                handle_proxy_407(url, session)
                # try again
                return download(url, dst_path, session=session, md5=md5,
                                urlstxt=urlstxt, retries=retries, ssl_verify=ssl_verify)
            msg = "Connection error: %s: %s\n" % (e, url)
            stderrlog.info('Could not connect to %s\n' % url)
            log.debug(msg)
            raise RuntimeError(msg)

        except IOError as e:
            raise RuntimeError("Could not open '%s': %s" % (url, e))

        size = resp.headers.get('Content-Length')
        if size:
            size = int(size)
            fn = basename(dst_path)
            getLogger('fetch.start').info((fn[:14], size))

        n = 0
        if md5:
            h = hashlib.new('md5')
        try:
            with open(pp, 'wb') as fo:
                more = True
                while more:
                    # Use resp.raw so that requests doesn't decode gz files
                    chunk  = resp.raw.read(2**14)
                    if not chunk:
                        more = False
                    try:
                        fo.write(chunk)
                    except IOError:
                        raise RuntimeError("Failed to write to %r." % pp)
                    if md5:
                        h.update(chunk)
                    # update n with actual bytes read
                    n = resp.raw.tell()
                    if size and 0 <= n <= size:
                        getLogger('fetch.update').info(n)
        except IOError as e:
            if e.errno == 104 and retries: # Connection reset by pee
                # try again
                log.debug("%s, trying again" % e)
                return download(url, dst_path, session=session, md5=md5,
                                urlstxt=urlstxt, retries=retries-1, ssl_verify=ssl_verify)
            raise RuntimeError("Could not open %r for writing (%s)." % (pp, e))

        if size:
            getLogger('fetch.stop').info(None)

        if md5 and h.hexdigest() != md5:
            if retries:
                # try again
                log.debug("MD5 sums mismatch for download: %s (%s != %s), "
                          "trying again" % (url, h.hexdigest(), md5))
                return download(url, dst_path, session=session, md5=md5,
                                urlstxt=urlstxt, retries=retries-1, ssl_verify=ssl_verify)
            raise RuntimeError("MD5 sums mismatch for download: %s (%s != %s)"
                               % (url, h.hexdigest(), md5))

        try:
            os.rename(pp, dst_path)
        except OSError as e:
            raise RuntimeError("Could not rename %r to %r: %r" %
                               (pp, dst_path, e))

        if urlstxt:
            try:
                with open(join(dst_dir, 'urls.txt'), 'a') as fa:
                    fa.write('%s\n' % url)
            except IOError:
                pass


class TmpDownload(object):
    """
    Context manager to handle downloads to a tempfile
    """
    def __init__(self, url, verbose=True):
        self.url = url
        self.verbose = verbose

    def __enter__(self):
        if '://' not in self.url:
            # if we provide the file itself, no tmp dir is created
            self.tmp_dir = None
            return self.url
        else:
            if self.verbose:
                from conda.console import setup_handlers
                setup_handlers()
            self.tmp_dir = tempfile.mkdtemp()
            dst = join(self.tmp_dir, basename(self.url))
            download(self.url, dst)
            return dst

    def __exit__(self, exc_type, exc_value, traceback):
        if self.tmp_dir:
            shutil.rmtree(self.tmp_dir)