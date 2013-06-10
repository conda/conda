import re
import sys
from subprocess import check_call, CalledProcessError
from os.path import isfile, join

from packup import untracked, packup_and_reinstall


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
