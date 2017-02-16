# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
from os.path import basename, isdir, join, lexists, isfile, dirname
from tempfile import gettempdir
from unittest import TestCase
from uuid import uuid4

import sys

from conda import CONDA_PACKAGE_ROOT

from conda._vendor.toolz.itertoolz import groupby

from conda._vendor.auxlib.collection import AttrDict
from conda.base.context import context

from conda.common.path import get_python_site_packages_short_path, get_python_noarch_target_path, \
    get_python_short_path, pyc_path, parse_entry_point_def, get_bin_directory_short_path, \
    win_path_ok
from conda.core.path_actions import LinkPathAction, CompilePycAction, CreatePythonEntryPointAction
from conda.gateways.disk.create import mkdir_p, create_link
from conda.gateways.disk.delete import rm_rf
from conda.gateways.disk.read import is_exe, compute_md5sum
from conda.gateways.disk.link import islink, stat_nlink
from conda.models.enums import LinkType, NoarchType
from conda.common.compat import PY2, on_win

log = getLogger(__name__)


def make_test_file(target_dir, suffix=''):
    if not isdir(target_dir):
        mkdir_p(target_dir)
    fn = str(uuid4())[:8]
    full_path = join(target_dir, fn + suffix)
    with open(full_path, 'w') as fh:
        fh.write(str(uuid4()))
    return full_path


def load_python_file(py_file_full_path):
    if PY2:
        import imp
        return imp.load_compiled("module.name", py_file_full_path)
    elif sys.version_info < (3, 5):
        raise RuntimeError("this doesn't work for .pyc files")
        from importlib.machinery import SourceFileLoader
        return SourceFileLoader("module.name", py_file_full_path).load_module()
    else:
        import importlib.util
        spec = importlib.util.spec_from_file_location("module.name", py_file_full_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


class PathActionsTests(TestCase):

    def setUp(self):
        tempdirdir = gettempdir()

        prefix_dirname = str(uuid4())[:8]
        self.prefix = join(tempdirdir, prefix_dirname)
        mkdir_p(self.prefix)
        assert isdir(self.prefix)

        pkgs_dirname = str(uuid4())[:8]
        self.pkgs_dir = join(tempdirdir, pkgs_dirname)
        mkdir_p(self.pkgs_dir)
        assert isdir(self.pkgs_dir)

    def tearDown(self):
        rm_rf(self.prefix)
        assert not lexists(self.prefix)
        rm_rf(self.pkgs_dir)
        assert not lexists(self.pkgs_dir)

    def test_CompilePycAction_generic(self):
        package_info = AttrDict(package_metadata=AttrDict(noarch=AttrDict(type=NoarchType.generic)))
        noarch = package_info.package_metadata and package_info.package_metadata.noarch
        assert noarch.type == NoarchType.generic
        axns = CompilePycAction.create_actions({}, package_info, self.prefix, None, ())
        assert axns == ()

        package_info = AttrDict(package_metadata=None)
        axns = CompilePycAction.create_actions({}, package_info, self.prefix, None, ())
        assert axns == ()

    def test_CompilePycAction_noarch_python(self):
        target_python_version = '%d.%d' % sys.version_info[:2]
        sp_dir = get_python_site_packages_short_path(target_python_version)
        transaction_context = {
            'target_python_version': target_python_version,
            'target_site_packages_short_path': sp_dir,
        }
        package_info = AttrDict(package_metadata=AttrDict(noarch=AttrDict(type=NoarchType.python)))

        file_link_actions = [
            AttrDict(
                source_short_path='site-packages/something.py',
                target_short_path=get_python_noarch_target_path('site-packages/something.py', sp_dir),
            ),
            AttrDict(
                # this one shouldn't get compiled
                source_short_path='something.py',
                target_short_path=get_python_noarch_target_path('something.py', sp_dir),
            ),
        ]
        axns = CompilePycAction.create_actions(transaction_context, package_info, self.prefix,
                                               None, file_link_actions)

        assert len(axns) == 1
        axn = axns[0]
        assert axn.source_full_path == join(self.prefix, win_path_ok(get_python_noarch_target_path('site-packages/something.py', sp_dir)))
        assert axn.target_full_path == join(self.prefix, win_path_ok(pyc_path(get_python_noarch_target_path('site-packages/something.py', sp_dir), target_python_version)))

        # make .py file in prefix that will be compiled
        mkdir_p(dirname(axn.source_full_path))
        with open(axn.source_full_path, 'w') as fh:
            fh.write("value = 42\n")

        # symlink the current python
        python_full_path = join(self.prefix, get_python_short_path(target_python_version))
        mkdir_p(dirname(python_full_path))
        create_link(sys.executable, python_full_path, LinkType.softlink)

        axn.execute()
        assert isfile(axn.target_full_path)

        # remove the source .py file so we're sure we're importing the pyc file below
        rm_rf(axn.source_full_path)
        assert not isfile(axn.source_full_path)

        if (3, ) > sys.version_info >= (3, 5):
            # we're probably dropping py34 support soon enough anyway
            imported_pyc_file = load_python_file(axn.target_full_path)
            assert imported_pyc_file.value == 42

        axn.reverse()
        assert not isfile(axn.target_full_path)

    def test_CreatePythonEntryPointAction_generic(self):
        package_info = AttrDict(package_metadata=None)
        axns = CreatePythonEntryPointAction.create_actions({}, package_info, self.prefix, None)
        assert axns == ()

    def test_CreatePythonEntryPointAction_noarch_python(self):
        target_python_version = '%d.%d' % sys.version_info[:2]
        transaction_context = {
            'target_python_version': target_python_version,
        }
        package_info = AttrDict(package_metadata=AttrDict(noarch=AttrDict(
            type=NoarchType.python,
            entry_points=(
                'command1=some.module:main',
                'command2=another.somewhere:go',
            ),
        )))

        axns = CreatePythonEntryPointAction.create_actions(transaction_context, package_info,
                                                           self.prefix, LinkType.hardlink)
        grouped_axns = groupby(lambda ax: isinstance(ax, LinkPathAction), axns)
        windows_exe_axns = grouped_axns.get(True, ())
        assert len(windows_exe_axns) == (2 if on_win else 0)
        py_ep_axns = grouped_axns.get(False, ())
        assert len(py_ep_axns) == 2

        py_ep_axn = py_ep_axns[0]

        command, module, func = parse_entry_point_def('command1=some.module:main')
        assert command == 'command1'
        if on_win:
            target_short_path = "%s\\%s-script.py" % (get_bin_directory_short_path(), command)
        else:
            target_short_path = "%s/%s" % (get_bin_directory_short_path(), command)
        assert py_ep_axn.target_full_path == join(self.prefix, target_short_path)
        assert py_ep_axn.module == module == 'some.module'
        assert py_ep_axn.func == func == 'main'

        mkdir_p(dirname(py_ep_axn.target_full_path))
        py_ep_axn.execute()
        assert isfile(py_ep_axn.target_full_path)
        assert is_exe(py_ep_axn.target_full_path)
        with open(py_ep_axn.target_full_path) as fh:
            lines = fh.readlines()
            first_line = lines[0].strip()
            last_line = lines[-1].strip()
        if not on_win:
            python_full_path = join(self.prefix, get_python_short_path(target_python_version))
            assert first_line == "#!%s" % python_full_path
        assert last_line == "exit(%s())" % func

        py_ep_axn.reverse()
        assert not isfile(py_ep_axn.target_full_path)

        if on_win:
            windows_exe_axn = windows_exe_axns[0]
            target_short_path = "%s\\%s.exe" % (get_bin_directory_short_path(), command)
            assert windows_exe_axn.target_full_path == join(self.prefix, target_short_path)

            mkdir_p(dirname(windows_exe_axn.target_full_path))
            windows_exe_axn.verify()
            windows_exe_axn.execute()
            assert isfile(windows_exe_axn.target_full_path)
            assert is_exe(windows_exe_axn.target_full_path)

            src = compute_md5sum(join(CONDA_PACKAGE_ROOT, 'resources', 'cli-%d.exe' % context.bits))
            assert src == compute_md5sum(windows_exe_axn.target_full_path)

            windows_exe_axn.reverse()
            assert not isfile(windows_exe_axn.target_full_path)

    def test_simple_LinkPathAction_hardlink(self):
        source_full_path = make_test_file(self.pkgs_dir)
        target_short_path = source_short_path = basename(source_full_path)
        axn = LinkPathAction({}, None, self.pkgs_dir, source_short_path, self.prefix,
                             target_short_path, LinkType.hardlink)

        assert axn.target_full_path == join(self.prefix, target_short_path)
        axn.verify()
        axn.execute()
        assert isfile(axn.target_full_path)
        assert not islink(axn.target_full_path)
        assert stat_nlink(axn.target_full_path) == 2

        axn.reverse()
        assert not lexists(axn.target_full_path)

    def test_simple_LinkPathAction_softlink(self):
        source_full_path = make_test_file(self.pkgs_dir)
        target_short_path = source_short_path = basename(source_full_path)
        axn = LinkPathAction({}, None, self.pkgs_dir, source_short_path, self.prefix,
                             target_short_path, LinkType.softlink)

        assert axn.target_full_path == join(self.prefix, target_short_path)
        axn.verify()
        axn.execute()
        assert isfile(axn.target_full_path)
        assert islink(axn.target_full_path)
        assert stat_nlink(axn.target_full_path) == 1

        axn.reverse()
        assert not lexists(axn.target_full_path)
        assert lexists(source_full_path)

    def test_simple_LinkPathAction_directory(self):
        target_short_path = join('a', 'nested', 'directory')
        axn = LinkPathAction({}, None, None, None, self.prefix,
                             target_short_path, LinkType.directory)
        axn.verify()
        axn.execute()

        assert isdir(join(self.prefix, target_short_path))

        axn.reverse()
        assert not lexists(axn.target_full_path)
        assert not lexists(dirname(axn.target_full_path))
        assert not lexists(dirname(dirname(axn.target_full_path)))

    def test_simple_LinkPathAction_copy(self):
        source_full_path = make_test_file(self.pkgs_dir)
        target_short_path = source_short_path = basename(source_full_path)
        axn = LinkPathAction({}, None, self.pkgs_dir, source_short_path, self.prefix,
                             target_short_path, LinkType.copy)

        assert axn.target_full_path == join(self.prefix, target_short_path)
        axn.verify()
        axn.execute()
        assert isfile(axn.target_full_path)
        assert not islink(axn.target_full_path)
        assert stat_nlink(axn.target_full_path) == 1

        axn.reverse()
        assert not lexists(axn.target_full_path)
