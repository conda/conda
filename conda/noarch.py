import os
from os.path import dirname, exists, isdir, join, normpath
import sys
import shutil

PREFIX = normpath(sys.prefix)
FILES = []
if sys.platform == 'win32':
    BIN_DIR = join(PREFIX, 'Scripts')
    SITE_PACKAGES = 'Lib/site-packages'
else:
    BIN_DIR = join(PREFIX, 'bin')
    SITE_PACKAGES = 'lib/python%s/site-packages' % sys.version[:3]


def get_noarch_cls(noarch_type):
    return NOARCH_CLASSES.get(str(noarch_type).lower(), NoArch) if noarch_type else None


def link_package(src, dst):
    try:
        os.link(src, dst)
        # on Windows os.link raises AttributeError
    except (OSError, AttributeError):
        shutil.copy2(src, dst)


def unlink_package(path):
    try:
        os.unlink(path)
    except OSError:
        pass


class NoArch(object):

    def link(self, src_dir):
        pass

    def unlink(self):
        pass


class NoArchPython(NoArch):

    def link(self, src_dir):
        # map directories (site-packages)
        # deal with setup.py scripts (copied into right dir)
        # deal with entry points
        # compile pyc files

        # DATA is a list of files in site-packages
        # that is inside src_dir/site-packages

        # create_scripts(DATA['python-scripts'])
        link_files('site-packages', SITE_PACKAGES, list_site_package(src_dir), src_dir)
        with open(join(PREFIX, 'conda-meta.files'), 'w') as fo:
            for f in FILES:
                fo.write('%s\n' % f)

    def unlink(self):
        pass


def get_files_in_dir(src_dir):
    return [os.path.join(src_dir, fn) for fn in next(
        os.walk(src_dir))[2]]


def get_dirs_in_dir(src_dir):
    return [os.path.join(src_dir, fn) for fn in next(
        os.walk(src_dir))[1]]


def get_all_files_in_dir(src_dir):
    files = []
    files.extend(get_files_in_dir(src_dir))
    paths = get_dirs_in_dir(src_dir)
    for path in paths:
        files.extend(get_all_files_in_dir(path))
    return files


def list_site_package(src_dir):
    site_packages_dir = os.path.join(src_dir, "site-packages")
    return get_all_files_in_dir(site_packages_dir)


def link_files(src_root, dst_root, files, src_dir):
    for f in files:
        src = join(src_dir, src_root, f)
        dst = join(PREFIX, dst_root, f)
        dst_dir = dirname(dst)
        if not isdir(dst_dir):
            os.makedirs(dst_dir)
        if exists(dst):
            unlink_package(dst)
        link_package(src, dst)
        # TODO: do we need to keep track of files?
        # f = '%s/%s' % (dst_root, f)
        # FILES.append(f)
        # if f.endswith('.py'):
        #     FILES.append(pyc_f(f))


NOARCH_CLASSES = {
    'python': NoArchPython,
    True: NoArch,
}








