import os
from os.path import dirname, exists, isdir, join, normpath
import sys
import shutil
from subprocess import call

from conda.base.context import context
from conda.compat import itervalues


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
    record = next((record for record in itervalues(linked_data_[prefix]) if record.name == 'python'), None)
    if record is not None:
        return record.version
    raise RuntimeError()


def get_site_packages(prefix):
    if sys.platform == 'win32':
        return 'Lib'
    else:
        return'lib/python%s' % get_python_version_for_prefix(prefix)


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


def compile_missing_pyc(prefix, files, cwd):
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
        cache_prefix = ("__pycache__" + os.sep) if get_python_version_for_prefix(prefix) == 3 else ""
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
        with open(join(src_dir, "info/files")) as f:
            files = f.read()
        files = files.split("\n")[:-1]

        site_package_files = []
        bin_files = []
        for f in files:
            if f.find("site-packages"):
                site_package_files.append(f[f.find("site-packages"):])
            else:
                bin_files.append(f)

        prefix = context.default_prefix
        site_packages = get_site_packages(prefix)
        linked_files = link_files(prefix, '', site_packages, site_package_files, src_dir)
        compile_missing_pyc(
            prefix, linked_files, os.path.join(prefix, site_packages, 'site-packages')
        )

    def unlink(self):
        pass


NOARCH_CLASSES = {
    'python': NoArchPython,
    True: NoArch,
}
