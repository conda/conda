import re
import os
import sys
import json
import shutil
from subprocess import Popen, PIPE, check_call, CalledProcessError
from os.path import dirname, isfile, join

from packup import untracked, packup_and_reinstall
from source import get_source


def to_name(s):
    s = s.strip()
    pat = re.compile(r'[\w.\-]+')
    m = pat.match(s)
    if m is None:
        raise RuntimeError('could not determine package name from: %r' % s)
    return m.group(0)


def pip(prefix, pkg_request):
    if sys.platform == 'win32':
        pip_path = join(prefix, 'Scripts', 'pip.bat')
    else:
        pip_path = join(prefix, 'bin', 'pip')

    if not isfile(pip_path):
        raise RuntimeError('pip does not appear to be installed in prefix: '
                           '%r' % prefix)

    files_before = untracked(prefix)
    try:
        check_call([pip_path, 'install', pkg_request])
    except CalledProcessError:
        return
    packup_and_reinstall(prefix, files_before, to_name(pkg_request))


def build(prefix, url, source_type):
    print 'source_type:', source_type
    tmp_dir, src_dir = get_source(url, source_type)
    if src_dir is None:
        print "Could not locate source directory"
        return
    print 'src_dir:', src_dir

    if sys.platform == 'win32':
        python_path = join(prefix, 'python.exe')
    else:
        python_path = join(prefix, 'bin', 'python')

    try:
        p = Popen([python_path, 'setup.py', '--fullname'],
                  cwd=src_dir, stdout=PIPE, stderr=PIPE)
        fullname = p.communicate()[0].split()[-1]
        pkg_name, pkg_version = fullname.rsplit('-', 1)
    except:
        pkg_name, pkg_version = 'unknown', '0.0'

    files_before = untracked(prefix)
    try:
        check_call([python_path, 'setup.py', 'install'], cwd=src_dir)
    except CalledProcessError:
        return
    packup_and_reinstall(prefix, files_before, pkg_name, pkg_version)

    if tmp_dir:
        shutil.rmtree(tmp_dir)


def launch(app_dir):
    with open(join(app_dir, 'meta.json')) as fi:
        meta = json.load(fi)
    # prepend the bin directory to the path
    fmt = r'%s\Scripts;%s' if sys.platform == 'win32' else '%s/bin:%s'
    os.environ['PATH'] = fmt % (dirname(app_dir), os.environ['PATH'])
    # call the entry script
    check_call(meta['entry'].split(), cwd=app_dir)


if __name__ == '__main__':
    launch('/Users/ilan/python/App/unknown')
