import os
import tarfile
import zipfile
import tempfile
from subprocess import check_call
from os.path import abspath, join, isfile


def find_source_dir(tmp_dir):
    for fn in os.listdir(tmp_dir) + ['.']:
        dir_path = abspath(join(tmp_dir, fn))
        if isfile(join(dir_path, 'setup.py')):
            return dir_path
    return None


def get_source(url, source_type):
    """
    return root source directory
    """
    if source_type == 'dir':
        return None, abspath(url)
    tmp_dir = tempfile.mkdtemp()
    if source_type == 'tar':
        t = tarfile.open(url)
        t.extractall(path=tmp_dir)
        t.close()
    elif source_type == 'zip':
        z = zipfile.ZipFile(url)
        z.extractall(path=tmp_dir)
        z.close()
    elif source_type == 'git':
        check_call(['git', 'clone', url], cwd=tmp_dir)
    elif source_type == 'svn':
        check_call(['svn', 'co', url], cwd=tmp_dir)
    else:
        raise Exception('No source type: %r' % source_type)

    src_dir = find_source_dir(tmp_dir)
    if not src_dir:
        print "Could not find setup.py"
        return
    return tmp_dir, src_dir
