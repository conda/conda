import re
import sys
import subprocess
from os.path import isfile, join

from packup import untracked, make_tarbz2


def pip(prefix, pkg_name):
    if sys.platform == 'win32':
        pip_path = join(prefix, 'Scripts', 'pip.bat')
    else:
        pip_path = join(prefix, 'bin', 'pip')

    if not isfile(pip_path):
        raise Exception('pip does not appear to be installed in prefix: %r'
                        % prefix)

    try:
        subprocess.check_call([pip_path, 'install', pkg_name])
    except subprocess.CalledProcessError:
        return

    pkg_version = '0.0'
    pat = re.compile(pkg_name + r'-([^\-]+)-', re.I)
    files = untracked(prefix)
    for f in files:
        if 'site-packages' in f:
            m = pat.search(f)
            if m:
                pkg_version = m.group(1)
                break

    make_tarbz2(prefix, name=pkg_name, version=pkg_version, files=files)
