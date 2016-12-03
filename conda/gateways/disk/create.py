# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from errno import EEXIST
from io import open
import json
from logging import getLogger
import os
from os import W_OK, access, chmod, getpid, makedirs
from os.path import basename, exists, isdir, isfile, islink, join
from shlex import split as shlex_split
import shutil
from subprocess import PIPE, Popen
import traceback

from ... import CondaError
from ..._vendor.auxlib.entity import EntityEncoder
from ..._vendor.auxlib.ish import dals
from ...base.constants import LinkType, UTF8
from ...base.context import context
from ...common.path import win_path_ok
from ...exceptions import ClobberError, CondaOSError
from ...gateways.disk.delete import backoff_unlink, rm_rf
from ...models.dist import Dist
from ...utils import on_win

log = getLogger(__name__)
stdoutlog = getLogger('stdoutlog')


entry_point_template = dals("""
# -*- coding: utf-8 -*-
if __name__ == '__main__':
    from sys import exit
    from %(module)s import %(func)s
    exit(%(func)s())
""")


def create_unix_entry_point(target_full_path, python_full_path, module, func):
    pyscript = entry_point_template % {'module': module, 'func': func}
    with open(target_full_path, 'w') as fo:
        fo.write('#!%s\n' % python_full_path)
        fo.write(pyscript)
    chmod(target_full_path, 0o755)


def create_windows_entry_point_py(target_full_path, module, func):
    pyscript = entry_point_template % {'module': module, 'func': func}
    with open(target_full_path, 'w') as fo:
        fo.write(pyscript)


# def create_windows_entry_point_exe(target_full_path, link_type):
#     exe_source = join(CONDA_PACKAGE_ROOT, 'resources', 'cli-%d.exe' % context.bits)
#     create_link(exe_source, target_full_path + '.exe', link_type=link_type)
#
#
# def create_entry_point(target_full_path, python_full_path, module, func, link_type):
#     pyscript = entry_point_template % {'module': module, 'func': func}
#
#     if on_win:
#         # create -script.py
#         with open(target_full_path + '-script.py', 'w') as fo:
#             fo.write(pyscript)
#
#         # link cli-XX.exe
#         create_link(join(CONDA_PACKAGE_ROOT, 'resources', 'cli-%d.exe' % context.bits),
#                     target_full_path + '.exe')
#         return [ep_path + '-script.py', ep_path + '.exe']
#     else:
#         with open(target_full_path, 'w') as fo:
#             fo.write('#!%s\n' % python_full_path)
#             fo.write(pyscript)
#         chmod(target_full_path, 0o755)
#         return [target_full_path]


# def create_entry_point_old(entry_point_def, prefix):
#     # returns a list of file paths created
#     command, module, func = parse_entry_point_def(entry_point_def)
#     ep_path = "%s/%s" % (get_bin_directory_short_path(), command)
#
#     pyscript = entry_point_template % {'module': module, 'func': func}
#
#     if on_win:
#         # create -script.py
#         with open(join(prefix, ep_path + '-script.py'), 'w') as fo:
#             fo.write(pyscript)
#
#         # link cli-XX.exe
#         create_link(join(CONDA_PACKAGE_ROOT, 'resources', 'cli-%d.exe' % context.bits),
#                     join(prefix, win_path_ok(ep_path + '.exe')))
#         return [ep_path + '-script.py', ep_path + '.exe']
#     else:
#         # create py file
#         with open(join(prefix, ep_path), 'w') as fo:
#             fo.write('#!%s\n' % join(prefix, get_bin_directory_short_path(), 'python'))
#             fo.write(pyscript)
#         chmod(join(prefix, ep_path), 0o755)
#         return [ep_path]


def write_conda_meta_record(prefix, record):
    # write into <env>/conda-meta/<dist>.json
    meta_dir = join(prefix, 'conda-meta')
    if not isdir(meta_dir):
        makedirs(meta_dir)
    dist = Dist(record)
    with open(join(meta_dir, dist.to_filename('.json')), 'w') as fo:
        json_str = json.dumps(record, indent=2, sort_keys=True, cls=EntityEncoder)
        if hasattr(json_str, 'decode'):
            json_str = json_str.decode(UTF8)
        fo.write(json_str)


def try_write(dir_path, heavy=False):
    """Test write access to a directory.

    Args:
        dir_path (str): directory to test write access
        heavy (bool): Actually create and delete a file, or do a faster os.access test.
           https://docs.python.org/dev/library/os.html?highlight=xattr#os.access

    Returns:
        bool

    """
    if not isdir(dir_path):
        return False
    if on_win or heavy:
        # try to create a file to see if `dir_path` is writable, see #2151
        temp_filename = join(dir_path, '.conda-try-write-%d' % getpid())
        try:
            with open(temp_filename, mode='wb') as fo:
                fo.write(b'This is a test file.\n')
            backoff_unlink(temp_filename)
            return True
        except (IOError, OSError):
            return False
        finally:
            backoff_unlink(temp_filename)
    else:
        return access(dir_path, W_OK)


def try_hard_link(pkgs_dir, prefix, dist):
    # Some file systems (e.g. BeeGFS) do not support hard-links
    # between files in different directories. Depending on the
    # file system configuration, a symbolic link may be created
    # instead. If a symbolic link is created instead of a hard link,
    # return False.

    dist = Dist(dist)
    src = join(pkgs_dir, dist.dist_name, 'info', 'index.json')
    dst = join(prefix, '.tmp-%s' % dist.dist_name)
    assert isfile(src), src
    assert not isfile(dst), dst
    try:
        if not isdir(prefix):
            makedirs(prefix)
        create_link(src, dst, LinkType.hardlink)
        return not islink(dst)
    except OSError:
        return False
    finally:
        rm_rf(dst)


def hardlink_supported(source_file, dest_dir):
    # Some file systems (e.g. BeeGFS) do not support hard-links
    # between files in different directories. Depending on the
    # file system configuration, a symbolic link may be created
    # instead. If a symbolic link is created instead of a hard link,
    # return False.
    test_file = join(dest_dir, '.tmp.' + basename(source_file))
    assert isfile(source_file), source_file
    assert isdir(dest_dir), dest_dir
    assert not exists(test_file), test_file
    try:
        create_link(source_file, test_file, LinkType.hardlink)
        return not islink(test_file)
    except (IOError, OSError):
        return False
    finally:
        rm_rf(test_file)


def softlink_supported(source_file, dest_dir):
    # On Windows, softlink creation is restricted to Administrative users by default. It can
    # optionally be enabled for non-admin users through explicit registry modification.
    test_path = join(dest_dir, '.tmp.' + basename(source_file))
    assert isfile(source_file), source_file
    assert isdir(dest_dir), dest_dir
    assert not exists(test_path), test_path
    try:
        create_link(source_file, test_path, LinkType.softlink)
        return islink(test_path)
    except (IOError, OSError):
        return False
    finally:
        rm_rf(test_path)


def make_menu(prefix, file_path, remove=False):
    """
    Create cross-platform menu items (e.g. Windows Start Menu)

    Passes all menu config files %PREFIX%/Menu/*.json to ``menuinst.install``.
    ``remove=True`` will remove the menu items.
    """
    if not on_win:
        return
    elif basename(prefix).startswith('_'):
        log.warn("Environment name starts with underscore '_'. Skipping menu installation.")
        return

    import menuinst
    try:
        menuinst.install(join(prefix, win_path_ok(file_path)), remove, prefix)
    except:
        stdoutlog.error("menuinst Exception:")
        stdoutlog.error(traceback.format_exc())


def mkdir_p(path):
    try:
        makedirs(path)
    except OSError as e:
        if e.errno == EEXIST and isdir(path):
            pass
        else:
            raise


if on_win:
    import ctypes
    from ctypes import wintypes

    CreateHardLink = ctypes.windll.kernel32.CreateHardLinkW
    CreateHardLink.restype = wintypes.BOOL
    CreateHardLink.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR,
                               wintypes.LPVOID]
    try:
        CreateSymbolicLink = ctypes.windll.kernel32.CreateSymbolicLinkW
        CreateSymbolicLink.restype = wintypes.BOOL
        CreateSymbolicLink.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR,
                                       wintypes.DWORD]
    except AttributeError:
        CreateSymbolicLink = None

    def win_hard_link(src, dst):
        "Equivalent to os.link, using the win32 CreateHardLink call."
        if not CreateHardLink(dst, src, None):
            raise CondaOSError('win32 hard link failed')

    def win_soft_link(src, dst):
        "Equivalent to os.symlink, using the win32 CreateSymbolicLink call."
        if CreateSymbolicLink is None:
            raise CondaOSError('win32 soft link not supported')
        if not CreateSymbolicLink(dst, src, isdir(src)):
            raise CondaOSError('win32 soft link failed')


def create_link(src, dst, link_type=LinkType.hardlink):
    if link_type == LinkType.directory:
        # A directory is technically not a link.  So link_type is a misnomer.
        #   Naming is hard.
        mkdir_p(dst)
        return

    if exists(dst):  # TODO: should this be lexists() ?
        if context.force:
            log.info("file exists, but clobbering: %r" % dst)
            rm_rf(dst)
        else:
            raise ClobberError(dst, src, link_type)
    if link_type == LinkType.hardlink:
        if on_win:
            win_hard_link(src, dst)
        else:
            os.link(src, dst)
    elif link_type == LinkType.softlink:
        if on_win:
            win_soft_link(src, dst)
        else:
            os.symlink(src, dst)
    elif link_type == LinkType.copy:
        # copy relative symlinks as symlinks
        if not on_win and islink(src) and not os.readlink(src).startswith('/'):
            os.symlink(os.readlink(src), dst)
        else:
            shutil.copy2(src, dst)
    else:
        raise CondaError("Did not expect linktype=%r" % link_type)


# def compile_missing_pyc(prefix, python_major_minor_version, files):
#     py_pyc_files = missing_pyc_files(python_major_minor_version, files)
#     python_exe = get_python_path()
#
#     with cwd(prefix):
#         py_files = (f[0] for f in py_pyc_files)
#         command = "%s -Wi -m py_compile %s" % (python_exe, ' '.join(py_files))
#         log.debug(command)
#         process = Popen(shlex_split(command), stdout=PIPE, stderr=PIPE)
#         stdout, stderr = process.communicate()
#
#     rc = process.returncode
#     if rc != 0:
#         log.debug("%s $  %s\n"
#                   "  stdout: %s\n"
#                   "  stderr: %s\n"
#                   "  rc: %d", prefix, command, stdout, stderr, rc)
#         raise RuntimeError()
#     pyc_files = tuple(f[1] for f in py_pyc_files)
#     return pyc_files

def _split_on_unix(command):
    # I guess windows doesn't like shlex.split
    return command if on_win else shlex_split(command)


def compile_pyc(python_exe_full_path, py_full_path):
    command = "%s -Wi -m py_compile %s" % (python_exe_full_path, py_full_path)
    log.trace(command)
    process = Popen(_split_on_unix(command), stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()

    rc = process.returncode
    if rc != 0:
        log.error("$ %s\n"
                  "  stdout: %s\n"
                  "  stderr: %s\n"
                  "  rc: %d", command, stdout, stderr, rc)
        raise RuntimeError()
