# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
from os.path import basename, dirname, isdir, isfile, join, lexists, getsize
import sys
from tempfile import gettempdir
from unittest import TestCase
from uuid import uuid4

import pytest

from conda.auxlib.collection import AttrDict
from conda._vendor.toolz.itertoolz import groupby
from conda.base.context import context
from conda.common.compat import PY2, on_win
from conda.common.path import get_bin_directory_short_path, get_python_noarch_target_path, \
    get_python_short_path, get_python_site_packages_short_path, parse_entry_point_def, pyc_path, \
    win_path_ok
from conda.core.path_actions import CompileMultiPycAction, CreatePythonEntryPointAction, LinkPathAction
from conda.exceptions import ParseError
from conda.gateways.disk.create import create_link, mkdir_p
from conda.gateways.disk.delete import rm_rf
from conda.gateways.disk.link import islink, stat_nlink
from conda.gateways.disk.permissions import is_executable
from conda.gateways.disk.read import compute_md5sum, compute_sha256sum
from conda.gateways.disk.test import softlink_supported
from conda.gateways.disk.update import touch
from conda.models.enums import LinkType, NoarchType, PathType
from conda.models.records import PathDataV1

log = getLogger(__name__)


def make_test_file(target_dir, suffix='', contents=''):
    if not isdir(target_dir):
        mkdir_p(target_dir)
    fn = str(uuid4())[:8]
    full_path = join(target_dir, fn + suffix)
    with open(full_path, 'w') as fh:
        fh.write(contents or str(uuid4()))
    return full_path


def load_python_file(py_file_full_path):
    if PY2:
        import imp
        return imp.load_compiled("module.name", py_file_full_path)
    elif sys.version_info < (3, 5):
        raise ParseError("this doesn't work for .pyc files")
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

        prefix_dirname = str(uuid4())[:4] + ' ' + str(uuid4())[:4] + '-prefix'
        self.prefix = join(tempdirdir, prefix_dirname)
        mkdir_p(self.prefix)
        assert isdir(self.prefix)

        pkgs_dirname = str(uuid4())[:4] + ' ' + str(uuid4())[:4]
        self.pkgs_dir = join(tempdirdir, pkgs_dirname)
        mkdir_p(self.pkgs_dir)
        assert isdir(self.pkgs_dir)

    def tearDown(self):
        rm_rf(self.prefix)
        if not (on_win and PY2):
            # this assertion fails for the Softlink action windows tests
            # line 141 in backoff_rmdir
            #  exp_backoff_fn(rmtree, path, onerror=retry, max_tries=max_tries)
            # leaves a directory self.prefix\\Scripts that cannot be accessed or removed
            assert not lexists(self.prefix)
        rm_rf(self.pkgs_dir)
        assert not lexists(self.pkgs_dir)

    def test_CompileMultiPycAction_generic(self):
        package_info = AttrDict(
            package_metadata=AttrDict(
                noarch=AttrDict(
                    type=NoarchType.generic))
        )
        noarch = package_info.package_metadata and package_info.package_metadata.noarch
        assert noarch.type == NoarchType.generic
        axns = CompileMultiPycAction.create_actions({}, package_info, self.prefix, None, ())
        assert axns == ()

        package_info = AttrDict(package_metadata=None)
        axns = CompileMultiPycAction.create_actions({}, package_info, self.prefix, None, ())
        assert axns == ()

    @pytest.mark.xfail(on_win, reason="pyc compilation need env on windows, see gh #8025")
    def test_CompileMultiPycAction_noarch_python(self):
        if not softlink_supported(__file__, self.prefix) and on_win:
            pytest.skip("softlink not supported")
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
                source_short_path='site-packages/another.py',
                target_short_path=get_python_noarch_target_path('site-packages/another.py', sp_dir),
            ),
            AttrDict(
                # this one shouldn't get compiled
                source_short_path='something.py',
                target_short_path=get_python_noarch_target_path('something.py', sp_dir),
            ),
            AttrDict(
                # this one shouldn't get compiled
                source_short_path='another.py',
                target_short_path=get_python_noarch_target_path('another.py', sp_dir),
            ),
        ]
        axns = CompileMultiPycAction.create_actions(transaction_context, package_info, self.prefix,
                                                    None, file_link_actions)

        assert len(axns) == 1
        axn = axns[0]
        source_full_paths = tuple(axn.source_full_paths)
        source_full_path0 = source_full_paths[0]
        source_full_path1 = source_full_paths[1]
        assert len(source_full_paths) == 2
        assert source_full_path0 == join(self.prefix, win_path_ok(get_python_noarch_target_path('site-packages/something.py', sp_dir)))
        assert source_full_path1 == join(self.prefix, win_path_ok(get_python_noarch_target_path('site-packages/another.py', sp_dir)))
        target_full_paths = tuple(axn.target_full_paths)
        target_full_path0 = target_full_paths[0]
        target_full_path1 = target_full_paths[1]
        assert len(target_full_paths) == 2
        assert target_full_path0 == join(self.prefix, win_path_ok(pyc_path(get_python_noarch_target_path('site-packages/something.py', sp_dir),
                     target_python_version)))
        assert target_full_path1 == join(self.prefix, win_path_ok(pyc_path(get_python_noarch_target_path('site-packages/another.py', sp_dir),
                     target_python_version)))

        # make .py file in prefix that will be compiled
        mkdir_p(dirname(source_full_path0))
        with open(source_full_path0, 'w') as fh:
            fh.write("value = 42\n")
        mkdir_p(dirname(source_full_path1))
        with open(source_full_path1, 'w') as fh:
            fh.write("value = 43\n")

        # symlink the current python
        python_full_path = join(self.prefix, get_python_short_path(target_python_version))
        mkdir_p(dirname(python_full_path))
        create_link(sys.executable, python_full_path, LinkType.softlink)

        axn.execute()
        assert isfile(target_full_path0)
        assert isfile(target_full_path1)

        # remove the source .py file so we're sure we're importing the pyc file below
        rm_rf(source_full_path0)
        assert not isfile(source_full_path0)
        rm_rf(source_full_path1)
        assert not isfile(source_full_path1)

        if (3,) > sys.version_info >= (3, 5):
            # we're probably dropping py34 support soon enough anyway
            imported_pyc_file = load_python_file(target_full_path0)
            assert imported_pyc_file.value == 42
            imported_pyc_file = load_python_file(target_full_path1)
            assert imported_pyc_file.value == 43

        axn.reverse()
        assert not isfile(target_full_path0)
        assert not isfile(target_full_path1)

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
        if not on_win:
            assert is_executable(py_ep_axn.target_full_path)
        with open(py_ep_axn.target_full_path) as fh:
            lines = fh.readlines()
            first_line = lines[0].strip()
            last_line = lines[-1].strip()
        if not on_win:
            python_full_path = join(self.prefix, get_python_short_path(target_python_version))
            assert first_line == "#!%s" % python_full_path
        assert last_line == "sys.exit(%s())" % func

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
            assert is_executable(windows_exe_axn.target_full_path)

            src = compute_md5sum(join(context.conda_prefix, 'Scripts/conda.exe'))
            assert src == compute_md5sum(windows_exe_axn.target_full_path)

            windows_exe_axn.reverse()
            assert not isfile(windows_exe_axn.target_full_path)

    def test_simple_LinkPathAction_hardlink(self):
        source_full_path = make_test_file(self.pkgs_dir)
        target_short_path = source_short_path = basename(source_full_path)

        correct_sha256 = compute_sha256sum(source_full_path)
        correct_size_in_bytes = getsize(source_full_path)
        path_type = PathType.hardlink

        source_path_data = PathDataV1(
            _path = source_short_path,
            path_type=path_type,
            sha256=correct_sha256,
            size_in_bytes=correct_size_in_bytes,
        )

        axn = LinkPathAction({}, None, self.pkgs_dir, source_short_path, self.prefix,
                             target_short_path, LinkType.hardlink, source_path_data)

        assert axn.target_full_path == join(self.prefix, target_short_path)
        axn.verify()
        axn.execute()
        assert isfile(axn.target_full_path)
        assert not islink(axn.target_full_path)
        assert stat_nlink(axn.target_full_path) == 2

        axn.reverse()
        assert not lexists(axn.target_full_path)

    def test_simple_LinkPathAction_softlink(self):
        if not softlink_supported(__file__, self.prefix) and on_win:
            pytest.skip("softlink not supported")

        source_full_path = make_test_file(self.pkgs_dir)
        target_short_path = source_short_path = basename(source_full_path)

        correct_sha256 = compute_sha256sum(source_full_path)
        correct_size_in_bytes = getsize(source_full_path)
        path_type = PathType.hardlink

        source_path_data = PathDataV1(
            _path = source_short_path,
            path_type=path_type,
            sha256=correct_sha256,
            size_in_bytes=correct_size_in_bytes,
        )

        axn = LinkPathAction({}, None, self.pkgs_dir, source_short_path, self.prefix,
                             target_short_path, LinkType.softlink, source_path_data)

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
                             target_short_path, LinkType.directory, None)
        axn.verify()
        axn.execute()

        assert isdir(join(self.prefix, target_short_path))

        axn.reverse()
        # this is counter-intuitive, but it's faster to tell conda to ignore folders for removal in transactions
        #    than it is to try to have it scan to see if anything else has populated that folder.
        assert lexists(axn.target_full_path)
        assert lexists(dirname(axn.target_full_path))
        assert lexists(dirname(dirname(axn.target_full_path)))

    def test_simple_LinkPathAction_copy(self):
        source_full_path = make_test_file(self.pkgs_dir)
        target_short_path = source_short_path = basename(source_full_path)

        correct_sha256 = compute_sha256sum(source_full_path)
        correct_size_in_bytes = getsize(source_full_path)
        path_type = PathType.hardlink

        source_path_data = PathDataV1(
            _path = source_short_path,
            path_type=path_type,
            sha256=correct_sha256,
            size_in_bytes=correct_size_in_bytes,
        )

        axn = LinkPathAction({}, None, self.pkgs_dir, source_short_path, self.prefix,
                             target_short_path, LinkType.copy, source_path_data)

        assert axn.target_full_path == join(self.prefix, target_short_path)
        axn.verify()
        axn.execute()
        assert isfile(axn.target_full_path)
        assert not islink(axn.target_full_path)
        assert stat_nlink(axn.target_full_path) == 1

        axn.reverse()
        assert not lexists(axn.target_full_path)

    # @pytest.mark.skipif(on_win, reason="unix-only test")
    # def test_CreateApplicationSoftlinkAction_basic_symlink_unix(self):
    #     from conda.core.path_actions import CreateApplicationSoftlinkAction
    #
    #     source_prefix = join(self.prefix, 'envs', '_yellow_')
    #     test_file = make_test_file(join(source_prefix, 'bin'), suffix='', contents='echo yellow')
    #     test_file = test_file[len(source_prefix) + 1:]
    #
    #     assert check_output(
    #         shlex_split("sh -c '. \"%s\"'" % join(source_prefix, test_file))).strip() == b"yellow"
    #
    #     package_info = AttrDict(
    #         index_json_record=AttrDict(name="yellow_package"),
    #         repodata_record=AttrDict(preferred_env="yellow"),
    #         package_metadata=AttrDict(
    #             preferred_env=AttrDict(
    #                 softlink_paths=[
    #                     test_file,
    #                 ]
    #             )
    #         ),
    #     )
    #     target_full_path = join(self.prefix, test_file)
    #     mkdir_p(join(dirname(target_full_path)))
    #
    #     with env_var("CONDA_ROOT_PREFIX", self.prefix, stack_callback=conda_tests_ctxt_mgmt_def_pol):
    #         axns = CreateApplicationSoftlinkAction.create_actions({}, package_info, source_prefix,
    #                                                               None)
    #         assert len(axns) == 1
    #         axn = axns[0]
    #
    #         assert axn.target_full_path == target_full_path
    #         axn.verify()
    #         axn.execute()
    #         assert islink(axn.target_full_path)
    #         assert check_output(shlex_split("sh -c '. \"%s\"'" % axn.target_full_path)).strip() == b"yellow"
    #         axn.reverse()
    #         assert not lexists(axn.target_full_path)

    # @pytest.mark.skipif(not on_win, reason="windows-only test")
    # def test_CreateApplicationSoftlinkAction_basic_symlink_windows_not_supported(self):
    #
    #     source_prefix = join(self.prefix, 'envs', '_green_')
    #     mkdir_p(join(source_prefix, 'conda-meta'))
    #     touch(join(source_prefix, 'conda-meta', 'history'))
    #
    #     test_file_1 = make_test_file(join(source_prefix, 'Scripts'), suffix='',
    #                                  contents='echo red')
    #     test_file_1 = test_file_1[len(source_prefix) + 1:]
    #     assert check_output(shlex_split("sh -c '. \"%s\"'" % join(source_prefix, test_file_1))).strip() == b"red"
    #
    #     test_file_2 = make_test_file(join(source_prefix, 'Scripts'), suffix='.bat',
    #                                  contents='@echo off\necho blue')
    #     test_file_2 = test_file_2[len(source_prefix) + 1:]
    #     assert check_output(shlex_split("cmd /C \"%s\"" % join(source_prefix, test_file_2))).strip() == b"blue"
    #
    #     package_info = AttrDict(
    #         index_json_record=AttrDict(name="green_package"),
    #         repodata_record=AttrDict(preferred_env="green"),
    #         package_metadata=AttrDict(
    #             preferred_env=AttrDict(
    #                 softlink_paths=[
    #                     test_file_1,
    #                     test_file_2,
    #                 ]
    #             )
    #         ),
    #     )
    #     target_full_path_1 = join(self.prefix, test_file_1)
    #     target_full_path_2 = join(self.prefix, test_file_2)
    #     mkdir_p(join(dirname(target_full_path_1)))
    #
    #     with env_var("CONDA_ROOT_PREFIX", self.prefix, stack_callback=conda_tests_ctxt_mgmt_def_pol):
    #         softlink_supported_test_file = join(source_prefix, PREFIX_MAGIC_FILE)
    #         from conda.gateways.disk.test import softlink_supported
    #         softlink_actually_supported = softlink_supported(softlink_supported_test_file,
    #                                                          context.root_prefix)
    #
    #         import conda.core.path_actions
    #         with patch.object(conda.core.path_actions, "softlink_supported") as softlink_supported_mock:
    #             softlink_supported_mock.return_value = False
    #
    #             from conda.core.path_actions import CreateApplicationSoftlinkAction
    #             axns = CreateApplicationSoftlinkAction.create_actions({}, package_info,
    #                                                                   source_prefix, None)
    #             assert len(axns) == 2
    #
    #             axn = axns[0]
    #             assert axn.target_full_path == target_full_path_1
    #             assert axn.softlink_method == "softlink_or_fail_ok"
    #             axn.verify()
    #             axn.execute()
    #             if softlink_actually_supported:
    #                 assert islink(axn.target_full_path)
    #                 assert check_output(shlex_split("sh -c '. \"%s\"'" % axn.target_full_path)).strip() == b"red"
    #             else:
    #                 assert not lexists(axn.target_full_path)
    #             axn.reverse()
    #             assert not lexists(axn.target_full_path)
    #
    #             axn = axns[1]
    #             assert axn.target_full_path == target_full_path_2
    #             assert axn.softlink_method == "fake_exe_softlink"
    #             axn.verify()
    #             axn.execute()
    #             assert isfile(axn.target_full_path)
    #             assert check_output(shlex_split("cmd /C \"%s\"" % axn.target_full_path)).strip() == b"blue"
    #             axn.reverse()
    #             assert not lexists(axn.target_full_path)

    # @pytest.mark.skipif(not on_win, reason="windows-only test")
    # def test_CreateApplicationSoftlinkAction_basic_symlink_windows_supported(self):
    #     source_prefix = join(self.prefix, 'envs', '_green_')
    #     mkdir_p(join(source_prefix, 'conda-meta'))
    #     touch(join(source_prefix, 'conda-meta', 'history'))
    #
    #     test_file_1 = make_test_file(join(source_prefix, 'Scripts'), suffix='',
    #                                  contents='echo red')
    #     test_file_1 = test_file_1[len(source_prefix) + 1:]
    #     assert check_output(shlex_split(
    #         "sh -c '. \"%s\"'" % join(source_prefix, test_file_1))).strip() == b"red"
    #
    #     test_file_2 = make_test_file(join(source_prefix, 'Scripts'), suffix='.bat',
    #                                  contents='@echo off\necho blue')
    #     test_file_2 = test_file_2[len(source_prefix) + 1:]
    #     assert check_output(shlex_split("cmd /C \"%s\"" % join(source_prefix, test_file_2))).strip() == b"blue"
    #
    #     package_info = AttrDict(
    #         index_json_record=AttrDict(name="green_package"),
    #         repodata_record=AttrDict(preferred_env="green"),
    #         package_metadata=AttrDict(
    #             preferred_env=AttrDict(
    #                 softlink_paths=[
    #                     test_file_1,
    #                     test_file_2,
    #                 ]
    #             )
    #         ),
    #     )
    #     target_full_path_1 = join(self.prefix, test_file_1)
    #     target_full_path_2 = join(self.prefix, test_file_2)
    #     mkdir_p(join(dirname(target_full_path_1)))
    #
    #     with env_var("CONDA_ROOT_PREFIX", self.prefix, stack_callback=conda_tests_ctxt_mgmt_def_pol):
    #         softlink_supported_test_file = join(source_prefix, PREFIX_MAGIC_FILE)
    #         from conda.gateways.disk.test import softlink_supported
    #         softlink_actually_supported = softlink_supported(softlink_supported_test_file,
    #                                                          context.root_prefix)
    #
    #         import conda.core.path_actions
    #         with patch.object(conda.core.path_actions, "softlink_supported") as softlink_supported_mock:
    #             softlink_supported_mock.return_value = True
    #
    #             CreateApplicationSoftlinkAction = conda.core.path_actions.CreateApplicationSoftlinkAction
    #             axns = CreateApplicationSoftlinkAction.create_actions({}, package_info,
    #                                                                   source_prefix, None)
    #             assert len(axns) == 2
    #
    #             axn = axns[0]
    #             assert axn.target_full_path == target_full_path_1
    #             assert axn.softlink_method == "softlink"
    #             axn.verify()
    #             if softlink_actually_supported:
    #                 axn.execute()
    #                 assert islink(axn.target_full_path)
    #                 assert check_output(shlex_split("sh -c '. \"%s\"'" % axn.target_full_path)).strip() == b"red"
    #             else:
    #                 with pytest.raises(AssertionError):
    #                     axn.execute()
    #             axn.reverse()
    #             assert not lexists(axn.target_full_path)
    #
    #             axn = axns[1]
    #             assert axn.target_full_path == target_full_path_2
    #             assert axn.softlink_method == "softlink"
    #             axn.verify()
    #             if softlink_actually_supported:
    #                 axn.execute()
    #                 assert isfile(axn.target_full_path)
    #                 assert check_output(shlex_split("cmd /C \"%s\"" % axn.target_full_path)).strip() == b"blue"
    #             else:
    #                 with pytest.raises(AssertionError):
    #                     axn.execute()
    #             axn.reverse()
    #             assert not lexists(axn.target_full_path)
