from __future__ import print_function, division, absolute_import

import re
import os
import sys
import stat
from glob import glob
from subprocess import call, check_call
from os.path import basename, islink, join, splitext

from conda.install import prefix_placeholder

from .config import build_prefix, build_python, PY3K
from .source import WORK_DIR
from . import external
from . import environ
from . import utils


if sys.platform == 'linux2':
    import elf
elif sys.platform == 'darwin':
    import macho



def is_obj(path):
    assert sys.platform != 'win32'
    return bool((sys.platform == 'linux2' and elf.is_elf(path)) or
                (sys.platform == 'darwin' and macho.is_macho(path)))



shebang_pat = re.compile(r'^#!.+$', re.M)
def fix_shebang(f, osx_is_app=False):
    path = join(build_prefix, f)
    if is_obj(path):
        return
    with open(path) as fi:
        data = fi.read()
    m = shebang_pat.match(data)
    if not (m and 'python' in m.group()):
        return

    py_exec = (prefix_placeholder + '/python.app/Contents/MacOS/python'
               if sys.platform == 'darwin' and osx_is_app else
               prefix_placeholder + '/bin/' + basename(build_python))
    new_data = shebang_pat.sub('#!' + py_exec, data, count=1)
    if new_data == data:
        return
    print("updating shebang:", f)
    with open(path, 'w') as fo:
        fo.write(new_data)
    os.chmod(path, 0755)


def rm_egg_dirs():
    "remove egg directories"
    sp_dir = environ.sp_dir
    egg_dirs = glob(join(sp_dir, '*-py*.egg'))
    for egg_dir in egg_dirs:
        print('moving egg dir:', egg_dir)
        try:
            os.rename(join(egg_dir, 'EGG-INFO/PKG-INFO'), egg_dir + '-info')
        except OSError:
            pass
        utils.rm_rf(join(egg_dir, 'EGG-INFO'))
        for fn in os.listdir(egg_dir):
            os.rename(join(egg_dir, fn), join(sp_dir, fn))
        utils.rm_rf(join(sp_dir, 'easy-install.pth'))

def rm_py_along_so():
    "remove .py (.pyc) files alongside .so or .pyd files"
    for root, dirs, files in os.walk(build_prefix):
        for fn in files:
            if fn.endswith(('.so', '.pyd')):
                name, unused_ext = splitext(fn)
                for ext in '.py', '.pyc':
                    if name + ext in files:
                        os.unlink(join(root, name + ext))


def compile_missing_pyc():
    sp_dir = environ.sp_dir

    need_compile = False
    for root, dirs, files in os.walk(sp_dir):
        for fn in files:
            if fn.endswith('.py') and fn + 'c' not in files:
                need_compile = True
    if need_compile:
        print('compiling .pyc files...')
        check_call([build_python, '-Wi', join(environ.stdlib_dir,
                                              'compileall.py'),
                    '-q', '-x', 'port_v3', sp_dir])


def post_process():
    rm_egg_dirs()
    rm_py_along_so()
    if not PY3K:
        compile_missing_pyc()


def osx_ch_link(path, link):
    assert path.startswith(build_prefix + '/')
    reldir = utils.rel_lib(path[len(build_prefix) + 1:])

    if link.startswith((build_prefix + '/lib', 'lib', '@executable_path/')):
        return '@loader_path/%s/%s' % (reldir, basename(link))

    if link == '/usr/local/lib/libgcc_s.1.dylib':
        return '/usr/lib/libgcc_s.1.dylib'

def mk_relative_osx(path):
    assert sys.platform == 'darwin' and is_obj(path)
    macho.install_name_change(path, osx_ch_link)

    if path.endswith('.dylib'):
        # note that not every MachO binaries is a "dynamically linked shared
        # library" which have an identification name, a .so C extensions
        # extensions is a "bundle".  One can verify this using the "file"
        # command.
        names = macho.otool(path)
        if names:
            args = ['install_name_tool', '-id', basename(names[0]), path]
            print(' '.join(args))
            check_call(args)

    for name in macho.otool(path):
        assert not name.startswith(build_prefix), path

def mk_relative(f):
    assert sys.platform != 'win32'
    if f.startswith('bin/'):
        fix_shebang(f)

    path = join(build_prefix, f)
    if sys.platform == 'linux2' and is_obj(path):
        runpath = '$ORIGIN/' + utils.rel_lib(f)
        chrpath = external.find_executable('chrpath')
        if chrpath is None:
            sys.exit("""\
Error:
    Did not find 'chrpath' in: %s
    'chrpath' is necessary for building conda packages on Linux with
    relocatable ELF libraries.  You can install chrpath using apt-get,
    yum or conda.
""" % (os.pathsep.join(external.dir_paths)))
        call([chrpath, '-c', '-r', runpath, path])

    if sys.platform == 'darwin' and is_obj(path):
        mk_relative_osx(path)


bi_pat = re.compile(WORK_DIR)
def replace_bi_path(path):
    if islink(path):
        return
    with open(path, 'r+b') as f:
        data = f.read()
        matches = list(bi_pat.finditer(data))
        if not matches:
            return
        print("Replacing build and install path in:", path)
        for m in matches:
            s = m.group(0)
            if s == WORK_DIR:
                t = 'src-dir'
            elif s == build_prefix:
                t = 'install-prefix'
            else:
                raise Exception("did not excpet to get here")
            d = len(s) - len(t)
            r = (d // 2 * '-' + t + (d // 2 + 3) * '-')[:len(s)]
            assert len(r) == len(s)
            assert m.start() + len(r) == m.end()
            f.seek(m.start())
            f.write(r)


def fix_permissions():
    for root, dirs, files in os.walk(build_prefix):
        for dn in dirs:
            os.chmod(join(root, dn), 0775)
        for fn in files:
            p = join(root, fn)
            st = os.stat(p)
            os.chmod(p, stat.S_IMODE(st.st_mode) | stat.S_IWUSR) # chmod u+w


def post_build(files):
    print('number of files:', len(files))
    fix_permissions()
    for f in files:
        if sys.platform != 'win32':
            mk_relative(f)
        replace_bi_path(join(build_prefix, f))
