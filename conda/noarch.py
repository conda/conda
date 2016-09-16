import os
from os.path import dirname, exists, isdir, join, normpath
import sys
import shutil
from subprocess import call

from conda.base.context import context
from conda.compat import itervalues
from conda.install import linked_data_

if sys.platform == 'win32':
    BIN_DIR = join(normpath(sys.prefix), 'Scripts')
    SITE_PACKAGES = 'Lib'
else:
    BIN_DIR = join(normpath(sys.prefix), 'bin')
    SITE_PACKAGES = 'lib/python%s' % sys.version[:3]


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


def get_python_version_for_prefix(prefix):
    import pdb; pdb.set_trace()

    record = next((record for record in itervalues(linked_data_[prefix]) if record.name == 'python'), None)
    if record is not None:
        return record.version
    raise RuntimeError()


def link_files(prefix, src_root, dst_root, files, src_dir):
    prefix = normpath(prefix)

    get_python_version_for_prefix(prefix)

    dst_files = []
    for f in files:
        src = join(src_dir, src_root, f)
        dst = join(prefix, dst_root, f)
        dst_dir = dirname(dst)
        dst_files.append(dst)
        if not isdir(dst_dir):
            os.makedirs(dst_dir)
        if exists(dst):
            unlink_package(dst)

        link_package(src, dst)
    return dst_files


def compile_missing_pyc(files, cwd):
    compile_files = []
    for fn in files:
        # omit files in Library/bin, Scripts, and the root prefix - they are not generally imported
        if sys.platform == 'win32':
            if any([fn.lower().startswith(start) for start in ['library/bin', 'library\\bin',
                                                               'scripts']]):
                continue
        else:
            if fn.startswith('bin'):
                continue
        cache_prefix = ("__pycache__" + os.sep) if sys.version_info.major == 3 else ""
        if (fn.endswith(".py") and
                os.path.dirname(fn) + cache_prefix + os.path.basename(fn) + 'c' not in files):
            compile_files.append(fn)

    if compile_files:
        print('compiling .pyc files...')
        for f in compile_files:
            call(["python", '-Wi', '-m', 'py_compile', f], cwd=cwd)


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
        # get python scripts and put them in bin/

        with open(join(src_dir, "info/files")) as f:
            files = f.read()
        files = files.split("\n")[:-1]

        linked_files = link_files(context.prefix, '', SITE_PACKAGES, files, src_dir)
        compile_missing_pyc(linked_files, os.path.join(sys.prefix, SITE_PACKAGES, 'site-packages'))

    def unlink(self):
        pass


NOARCH_CLASSES = {
    'python': NoArchPython,
    True: NoArch,
}
