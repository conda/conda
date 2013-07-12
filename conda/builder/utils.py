from __future__ import print_function, division, absolute_import

import os
import sys
import hashlib
import shutil
import tarfile
import zipfile
import subprocess
from os.path import (abspath, dirname, getmtime, getsize, isdir, isfile,
                     islink, join, normpath)

import sys
if sys.version_info < (3,):
    import urllib2
else:
    import urllib.request as urllib2

from conda.utils import md5_file



def rel_lib(f):
    assert not f.startswith('/')
    if f.startswith('lib/'):
        return normpath((f.count('/') - 1) * '../')
    else:
        return normpath(f.count('/') * '../') + '/lib'


def _check_call(args, **kwargs):
    try:
        subprocess.check_call(args, **kwargs)
    except subprocess.CalledProcessError:
        sys.exit('Command failed: %s' % ' '.join(args))


def url_path(path):
    path = abspath(path)
    if sys.platform == 'win32':
        path = '/' + path.replace(':', '|')
    return 'file://%s' % path


def download(url, dst_path, md5=None):
    try:
        fi = urllib2.urlopen(url)
    except urllib2.URLError:
        raise urllib2.URLError("Error could not open URL: %r" % url)
    data = fi.read()
    fi.close()
    if md5:
        assert hashlib.md5(data).hexdigest() == md5
    with open(dst_path, 'wb') as fo:
        fo.write(data)


def tar_xf(tarball, dir_path, mode='r:*'):
    if tarball.endswith('.tar.xz'):
        subprocess.check_call(['unxz', '-f', '-k', tarball])
        tarball = tarball[:-3]
    t = tarfile.open(tarball, mode)
    t.extractall(path=dir_path)
    t.close()


def unzip(zip_path, dir_path):
    z = zipfile.ZipFile(zip_path)
    for name in z.namelist():
        if name.endswith('/'):
            continue
        path = join(dir_path, *name.split('/'))
        dp = dirname(path)
        if not isdir(dp):
            os.makedirs(dp)
        with open(path, 'wb') as fo:
            fo.write(z.read(name))
    z.close()


def rm_rf(path):
    if islink(path) or isfile(path):
        os.unlink(path)

    elif isdir(path):
        if sys.platform == 'win32':
            subprocess.check_call(['cmd', '/c', 'rd', '/s', '/q', path])
        else:
            shutil.rmtree(path)


def file_info(path):
    return {'size': getsize(path),
            'md5': md5_file(path),
            'mtime': getmtime(path)}
