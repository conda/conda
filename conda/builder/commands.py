import sys
import subprocess
from os.path import isfile, join

from packup import packup_and_reinstall



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
    packup_and_reinstall(prefix, pkg_name)
