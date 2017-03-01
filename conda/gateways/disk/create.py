# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from errno import EACCES, EEXIST, EPERM
from io import open
import json
from logging import getLogger
import os
from os import makedirs
from os.path import basename, isdir, isfile, join, lexists
import shutil
import sys
import tarfile
import traceback

from .delete import rm_rf
from .link import islink, link, readlink, symlink
from .permissions import make_executable
from .read import get_json_content
from .update import touch
from ..subprocess import subprocess_call
from ... import CondaError
from ..._vendor.auxlib.entity import EntityEncoder
from ..._vendor.auxlib.ish import dals
from ...base.context import context
from ...common.compat import ensure_binary, on_win
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


def write_as_json_to_file(file_path, obj):
    log.trace("writing json to file %s", file_path)
    with open(file_path, str('wb')) as fo:
        json_str = json.dumps(obj, indent=2, sort_keys=True, separators=(',', ': '),
                              cls=EntityEncoder)
        fo.write(ensure_binary(json_str))


def create_unix_python_entry_point(target_full_path, python_full_path, module, func):
    if lexists(target_full_path):
        maybe_raise(BasicClobberError(
            source_path=None,
            target_path=target_full_path,
            context=context,
        ), context)

    pyscript = python_entry_point_template % {'module': module, 'func': func}
    with open(target_full_path, str('w')) as fo:
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
    with open(target_full_path, str('w')) as fo:
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
    write_as_json_to_file(conda_meta_full_path, record)


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
        link(src, dst)
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
        if not force:
            maybe_raise(BasicClobberError(src, dst, context), context)
        log.info("file exists, but clobbering: %r" % dst)
        rm_rf(dst)

    if link_type == LinkType.hardlink:
        if isdir(src):
            raise CondaError("Cannot hard link a directory. %s" % src)
        link(src, dst)
    elif link_type == LinkType.softlink:
        symlink(src, dst)
    elif link_type == LinkType.copy:
        # on unix, make sure relative symlinks stay symlinks
        if not on_win and islink(src):
            src_points_to = readlink(src)
            if not src_points_to.startswith('/'):
                # copy relative symlinks as symlinks
                symlink(src_points_to, dst)
                return
        shutil.copy2(src, dst)
    else:
        raise CondaError("Did not expect linktype=%r" % link_type)


def compile_pyc(python_exe_full_path, py_full_path, pyc_full_path):
    if lexists(pyc_full_path):
        maybe_raise(BasicClobberError(None, pyc_full_path, context), context)

    command = "%s -Wi -m py_compile %s" % (python_exe_full_path, py_full_path)
    log.trace(command)
    subprocess_call(command)

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


def create_private_envs_meta(pkg, root_prefix, private_env_prefix):
    # type: (str, str, str) -> ()
    path_to_conda_meta = join(root_prefix, "conda-meta")

    if not isdir(path_to_conda_meta):
        mkdir_p(path_to_conda_meta)

    private_envs_json = get_json_content(context.private_envs_json_path)
    private_envs_json[pkg] = private_env_prefix
    write_as_json_to_file(context.private_envs_json_path, private_envs_json)


def create_private_pkg_entry_point(source_full_path, target_full_path, python_full_path):
    if lexists(target_full_path):
        maybe_raise(BasicClobberError(
            source_path=None,
            target_path=target_full_path,
            context=context,
        ), context)

    entry_point = application_entry_point_template % {"source_full_path": source_full_path}
    with open(target_full_path, str("w")) as fo:
        fo.write('#!%s\n' % python_full_path)
        fo.write(entry_point)
    make_executable(target_full_path)


def create_package_cache_directory(pkgs_dir):
    # returns False if package cache directory cannot be created
    try:
        log.trace("creating package cache directory '%s'", pkgs_dir)
        mkdir_p(pkgs_dir)
        touch(join(pkgs_dir, 'urls'))
        touch(join(pkgs_dir, 'urls.txt'))
    except (IOError, OSError) as e:
        if e.errno in (EACCES, EPERM):
            log.trace("Cannot create package cache directory '%s'", pkgs_dir)
            return False
        else:
            raise
    return True
