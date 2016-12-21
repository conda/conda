# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from errno import EEXIST
from io import open
import json
from logging import getLogger
import os
from os import makedirs
from os.path import basename, isdir, isfile, islink, join, lexists
from shlex import split as shlex_split
import shutil
from subprocess import PIPE, Popen
import sys
import tarfile
import traceback

from .delete import rm_rf
from .permissions import make_executable
from ... import CondaError
from ..._vendor.auxlib.entity import EntityEncoder
from ..._vendor.auxlib.ish import dals
from ...base.constants import PRIVATE_ENVS
from ...base.context import context
from ...common.compat import on_win
from ...common.path import win_path_ok
from ...exceptions import BasicClobberError, CondaOSError, maybe_raise
from ...models.dist import Dist
from ...models.enums import LinkType

log = getLogger(__name__)
stdoutlog = getLogger('stdoutlog')


python_entry_point_template = dals("""
# -*- coding: utf-8 -*-
if __name__ == '__main__':
    from sys import exit
    from %(module)s import %(func)s
    exit(%(func)s())
""")

application_entry_point_template = dals("""
# -*- coding: utf-8 -*-
if __name__ == '__main__':
    import os
    import sys
    os.execv(%(source_full_path)s, sys.argv)
""")


def create_unix_python_entry_point(target_full_path, python_full_path, module, func):
    if lexists(target_full_path):
        maybe_raise(BasicClobberError(
            source_path=None,
            target_path=target_full_path,
            context=context,
        ), context)

    pyscript = python_entry_point_template % {'module': module, 'func': func}
    with open(target_full_path, 'w') as fo:
        fo.write('#!%s\n' % python_full_path)
        fo.write(pyscript)
    make_executable(target_full_path)

    return target_full_path


def create_windows_python_entry_point(target_full_path, module, func):
    if lexists(target_full_path):
        maybe_raise(BasicClobberError(
            source_path=None,
            target_path=target_full_path,
            context=context,
        ), context)

    pyscript = python_entry_point_template % {'module': module, 'func': func}
    with open(target_full_path, 'w') as fo:
        fo.write(pyscript)

    return target_full_path


def extract_tarball(tarball_full_path, destination_directory=None):
    if destination_directory is None:
        destination_directory = tarball_full_path[:-8]
    log.debug("extracting %s\n  to %s", tarball_full_path, destination_directory)

    assert not lexists(destination_directory), destination_directory

    with tarfile.open(tarball_full_path) as t:
        t.extractall(path=destination_directory)
    if sys.platform.startswith('linux') and os.getuid() == 0:
        # When extracting as root, tarfile will by restore ownership
        # of extracted files.  However, we want root to be the owner
        # (our implementation of --no-same-owner).
        for root, dirs, files in os.walk(destination_directory):
            for fn in files:
                p = join(root, fn)
                os.lchown(p, 0, 0)


def write_linked_package_record(prefix, record):
    # write into <env>/conda-meta/<dist>.json
    meta_dir = join(prefix, 'conda-meta')
    if not isdir(meta_dir):
        makedirs(meta_dir)
    dist = Dist(record)
    conda_meta_full_path = join(meta_dir, dist.to_filename('.json'))
    if lexists(conda_meta_full_path):
        maybe_raise(BasicClobberError(
            source_path=None,
            target_path=conda_meta_full_path,
            context=context,
        ), context)
    with open(conda_meta_full_path, 'w') as fo:
        json_str = json.dumps(record, indent=2, sort_keys=True, cls=EntityEncoder)
        if hasattr(json_str, 'decode'):
            json_str = json_str.decode('utf-8')
        fo.write(json_str)


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
        log.trace('making directory %s', path)
        if path:
            makedirs(path)
    except OSError as e:
        if e.errno == EEXIST and isdir(path):
            return path
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


def create_hard_link_or_copy(src, dst):
    if islink(src):
        message = dals("""
        Cannot hard link a soft link
          source: %(source_path)s
          destination: %(destination_path)s
        """ % {
            'source_path': src,
            'destination_path': dst,
        })
        raise CondaOSError(message)

    try:
        log.trace("creating hard link %s => %s", src, dst)
        if on_win:
            win_hard_link(src, dst)
        else:
            os.link(src, dst)
    except (IOError, OSError):
        log.info('hard link failed, so copying %s => %s', src, dst)
        shutil.copy2(src, dst)


def create_link(src, dst, link_type=LinkType.hardlink, force=False):
    if link_type == LinkType.directory:
        # A directory is technically not a link.  So link_type is a misnomer.
        #   Naming is hard.
        mkdir_p(dst)
        return

    if not lexists(src):
        raise CondaError("Cannot link a source that does not exist. %s" % src)

    if lexists(dst):
        if force:
            log.info("file exists, but clobbering: %r" % dst)
            rm_rf(dst)
        else:
            maybe_raise(BasicClobberError(src, dst, link_type), context)

    if link_type == LinkType.hardlink:
        if isdir(src):
            raise CondaError("Cannot hard link a directory. %s" % src)
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


def _split_on_unix(command):
    # I guess windows doesn't like shlex.split
    return command if on_win else shlex_split(command)


def compile_pyc(python_exe_full_path, py_full_path, pyc_full_path):
    if lexists(pyc_full_path):
        maybe_raise(BasicClobberError(None, pyc_full_path, context), context)

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

    if not isfile(pyc_full_path):
        message = dals("""
        pyc file failed to compile successfully
          python_exe_full_path: %(python_exe_full_path)s\n
          py_full_path: %(py_full_path)s\n
          pyc_full_path: %(pyc_full_path)s\n
        """)
        raise CondaError(message, python_exe_full_path=python_exe_full_path,
                         py_full_path=py_full_path, pyc_full_path=pyc_full_path)

    return pyc_full_path


def get_json_content(path_to_json):
    if isfile(path_to_json):
        try:
            with open(path_to_json, "r") as f:
                json_content = json.load(f)
        except json.decoder.JSONDecodeError:
            json_content = {}
    else:
        json_content = {}
    return json_content


def create_private_envs_meta(pkg, root_prefix, private_env_prefix):
    # type: (str, str, str) -> ()
    path_to_conda_meta = join(root_prefix, "conda-meta")

    if not isdir(path_to_conda_meta):
        mkdir_p(path_to_conda_meta)

    private_envs_json = get_json_content(PRIVATE_ENVS)
    private_envs_json[pkg] = private_env_prefix
    with open(PRIVATE_ENVS, "w") as f:
        json.dump(private_envs_json, f)


def remove_private_envs_meta(pkg):
    private_envs_json = get_json_content(PRIVATE_ENVS)
    if pkg in private_envs_json.keys():
        private_envs_json.pop(pkg)
    if private_envs_json == {}:
        rm_rf(PRIVATE_ENVS)
    else:
        with open(PRIVATE_ENVS, "w") as f:
            json.dump(private_envs_json, f)


def create_private_pkg_entry_point(source_full_path, target_full_path, python_full_path):
    if lexists(target_full_path):
        maybe_raise(BasicClobberError(
            source_path=None,
            target_path=target_full_path,
            context=context,
        ), context)

    entry_point = application_entry_point_template % {"source_full_path": source_full_path}
    with open(target_full_path, "w") as fo:
        fo.write('#!%s\n' % python_full_path)
        fo.write(entry_point)
    make_executable(target_full_path)
