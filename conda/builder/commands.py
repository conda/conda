import sys
import shutil
from subprocess import Popen, PIPE, check_call, CalledProcessError
from os.path import isfile, join

from packup import packup_and_reinstall
from source import get_source


def pip(prefix, pkg_name):
    if sys.platform == 'win32':
        pip_path = join(prefix, 'Scripts', 'pip.bat')
    else:
        pip_path = join(prefix, 'bin', 'pip')

    if not isfile(pip_path):
        raise RuntimeError('pip does not appear to be installed in prefix: '
                           '%r' % prefix)

    try:
        check_call([pip_path, 'install', pkg_name])
    except CalledProcessError:
        return
    packup_and_reinstall(prefix, pkg_name)


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

    try:
        check_call([python_path, 'setup.py', 'install'], cwd=src_dir)
    except CalledProcessError:
        return
    packup_and_reinstall(prefix, pkg_name, pkg_version)

    if tmp_dir:
        shutil.rmtree(tmp_dir)
