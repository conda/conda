import re
import sys
import subprocess
from os.path import isfile, join

from conda.config import PACKAGES_DIR
from conda.install import install_local_package
from packup import untracked, remove, make_tarbz2


def guess_pkg_version(files, pkg_name):
    """
    Guess the package version from (usually untracked) files.
    """
    pat = re.compile(r'site-packages[/\\]' + pkg_name + r'-([^\-]+)-', re.I)
    for f in files:
        m = pat.search(f)
        if m:
            return m.group(1)
    return '0.0'


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

    files = untracked(prefix)
    fn = make_tarbz2(prefix,
                     name=pkg_name,
                     version=guess_pkg_version(files, pkg_name),
                     files=files)
    if fn is None:
        return
    remove(prefix, files)
    install_local_package(fn, PACKAGES_DIR, prefix)
