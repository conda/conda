# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import absolute_import, division, print_function, unicode_literals


from glob import glob

from conda.auxlib.compat import Utf8NamedTemporaryFile
from conda._vendor.toolz.itertoolz import groupby
from conda.gateways.disk.permissions import make_read_only
from conda.models.channel import Channel
from conda.resolve import Resolve

from itertools import chain
import json
from json import loads as json_loads
from logging import DEBUG, INFO, getLogger
import os
from os.path import abspath, basename, dirname, exists, isdir, isfile, join, lexists, relpath, islink
import re
from shutil import copyfile, rmtree
from subprocess import check_call, check_output, Popen, PIPE
import sys
from textwrap import dedent
from unittest import TestCase
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
import requests

from conda import (
    CondaError,
    CondaMultiError,
    __version__ as CONDA_VERSION,
    CONDA_SOURCE_ROOT,
)
from conda.auxlib.ish import dals
from conda.base.constants import CONDA_PACKAGE_EXTENSIONS, SafetyChecks, PREFIX_MAGIC_FILE
from conda.base.context import Context, context, reset_context, conda_tests_ctxt_mgmt_def_pol
from conda.common.compat import (ensure_text_type, iteritems, string_types, text_type,
                                 on_win, on_mac)
from conda.common.io import env_var, stderr_log_level, env_vars
from conda.common.path import get_bin_directory_short_path, get_python_site_packages_short_path, \
    pyc_path
from conda.common.serialize import yaml_round_trip_load, json_dump
from conda.core.index import get_reduced_index
from conda.core.prefix_data import PrefixData, get_python_version_for_prefix
from conda.core.package_cache_data import PackageCacheData
from conda.core.subdir_data import create_cache_dir
from conda.exceptions import CommandArgumentError, DryRunExit, OperationNotAllowed, \
    PackagesNotFoundError, RemoveError, PackageNotInstalledError, \
    DisallowedPackageError, DirectoryNotACondaEnvironmentError, EnvironmentLocationNotFound, \
    CondaValueError
from conda.gateways.anaconda_client import read_binstar_tokens
from conda.gateways.disk.delete import rm_rf, path_is_clean
from conda.gateways.disk.update import touch
from conda.gateways.subprocess import subprocess_call, subprocess_call_with_clean_env, Response
from conda.models.match_spec import MatchSpec
from conda.models.version import VersionOrder

from conda.testing.cases import BaseTestCase
from conda.testing.integration import (
    BIN_DIRECTORY,
    PYTHON_BINARY,
    TEST_LOG_LEVEL,
    create_temp_location,
    get_shortcut_dir,
    make_temp_channel,
    make_temp_package_cache,
    make_temp_prefix,
    reload_config,
    run_command,
    Commands,
    package_is_installed,
    make_temp_env,
    tempdir,
    which_or_where,
    cp_or_copy,
    env_or_set,
)

log = getLogger(__name__)
stderr_log_level(TEST_LOG_LEVEL, 'conda')
stderr_log_level(TEST_LOG_LEVEL, 'requests')


@pytest.mark.integration
class IntegrationTests(BaseTestCase):

    def setUp(self):
        PackageCacheData.clear()

    def test_install_python2_and_search(self):
        with Utf8NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as env_txt:
            log.warning("Creating empty temporary environment txt file {}".format(env_txt))
            environment_txt = env_txt.name

        with patch('conda.core.envs_manager.get_user_environments_txt_file',
                   return_value=environment_txt) as _:
            with make_temp_env("python=2", use_restricted_unicode=on_win) as prefix:
                with env_var('CONDA_ALLOW_NON_CHANNEL_URLS', 'true', stack_callback=conda_tests_ctxt_mgmt_def_pol):
                    assert exists(join(prefix, PYTHON_BINARY))
                    assert package_is_installed(prefix, 'python=2')

                    run_command(Commands.CONFIG, prefix, "--add", "channels", "https://repo.continuum.io/pkgs/not-a-channel")

                    # regression test for #4513
                    run_command(Commands.CONFIG, prefix, "--add", "channels", "https://repo.continuum.io/pkgs/not-a-channel")
                    stdout, stderr, _ = run_command(Commands.SEARCH, prefix, "python", "--json")
                    packages = json.loads(stdout)
                    assert len(packages) == 1

                    stdout, stderr, _ = run_command(Commands.SEARCH, prefix, "python", "--json", "--envs")
                    envs_result = json.loads(stdout)
                    assert any(match['location'] == prefix for match in envs_result)

                    stdout, stderr, _ = run_command(Commands.SEARCH, prefix, "python", "--envs")
                    assert prefix in stdout
        os.unlink(environment_txt)

    def test_run_preserves_arguments(self):
        with make_temp_env('python=3') as prefix:
            echo_args_py = os.path.join(prefix, "echo-args.py")
            with open(echo_args_py, "w") as echo_args:
                echo_args.write("import sys\n")
                echo_args.write("for arg in sys.argv[1:]: print(arg)\n")
            # If 'two two' were 'two' this test would pass.
            args = ('one', 'two two', 'three')
            output, _, _ = run_command(Commands.RUN, prefix, 'python', echo_args_py, *args)
            os.unlink(echo_args_py)
            lines = output.split('\n')
            for i, line in enumerate(lines):
                if i < len(args):
                    assert args[i] == line.replace('\r', '')

    def test_create_install_update_remove_smoketest(self):
        with make_temp_env("python=3.5") as prefix:
            assert exists(join(prefix, PYTHON_BINARY))
            assert package_is_installed(prefix, 'python=3')

            run_command(Commands.INSTALL, prefix, 'flask=0.12')
            assert package_is_installed(prefix, 'flask=0.12.2')
            assert package_is_installed(prefix, 'python=3')

            run_command(Commands.INSTALL, prefix, '--force-reinstall', 'flask=0.12.2')
            assert package_is_installed(prefix, 'flask=0.12.2')
            assert package_is_installed(prefix, 'python=3')

            run_command(Commands.UPDATE, prefix, 'flask')
            assert not package_is_installed(prefix, 'flask=0.12.2')
            assert package_is_installed(prefix, 'flask')
            assert package_is_installed(prefix, 'python=3')

            run_command(Commands.REMOVE, prefix, 'flask')
            assert not package_is_installed(prefix, 'flask=0.*')
            assert package_is_installed(prefix, 'python=3')

            stdout, stderr, _ = run_command(Commands.LIST, prefix, '--revisions')
            assert not stderr
            assert " (rev 4)\n" in stdout
            assert " (rev 5)\n" not in stdout

            run_command(Commands.INSTALL, prefix, '--revision', '0')
            assert not package_is_installed(prefix, 'flask')
            assert package_is_installed(prefix, 'python=3')

    def test_install_broken_post_install_keeps_existing_folders(self):
        # regression test for https://github.com/conda/conda/issues/8258
        with make_temp_env("python=3.5") as prefix:
            assert exists(join(prefix, BIN_DIRECTORY))
            assert package_is_installed(prefix, 'python=3')

            run_command(Commands.INSTALL, prefix, '-c', 'conda-test', 'failing_post_link', use_exception_handler=True)
            assert exists(join(prefix, BIN_DIRECTORY))

    def test_safety_checks(self):
        # This test uses https://anaconda.org/conda-test/spiffy-test-app/0.5/download/noarch/spiffy-test-app-0.5-pyh6afbcc8_0.tar.bz2
        # which is a modification of https://anaconda.org/conda-test/spiffy-test-app/1.0/download/noarch/spiffy-test-app-1.0-pyh6afabb7_0.tar.bz2
        # as documented in info/README within that package.
        # I also had to fix the post-link script in the package by adding quotation marks to handle
        # spaces in path names.

        with make_temp_env() as prefix:
            with open(join(prefix, 'condarc'), 'a') as fh:
                fh.write("safety_checks: enabled\n")
                fh.write("extra_safety_checks: true\n")
            reload_config(prefix)
            assert context.safety_checks is SafetyChecks.enabled

            with pytest.raises(CondaMultiError) as exc:
                run_command(Commands.INSTALL, prefix, '-c', 'conda-test', 'spiffy-test-app=0.5')

            error_message = text_type(exc.value)
            message1 = dals("""
            The path 'site-packages/spiffy_test_app-1.0-py2.7.egg-info/top_level.txt'
            has an incorrect size.
              reported size: 32 bytes
              actual size: 16 bytes
            """)
            message2 = dals("has a sha256 mismatch.")
            assert message1 in error_message
            assert message2 in error_message

            with open(join(prefix, 'condarc'), 'w') as fh:
                fh.write("safety_checks: warn\n")
                fh.write("extra_safety_checks: true\n")
            reload_config(prefix)
            assert context.safety_checks is SafetyChecks.warn

            stdout, stderr, _ = run_command(Commands.INSTALL, prefix, '-c', 'conda-test', 'spiffy-test-app=0.5')
            assert message1 in stderr
            assert message2 in stderr
            assert package_is_installed(prefix, "spiffy-test-app=0.5")

        with make_temp_env() as prefix:
            with open(join(prefix, 'condarc'), 'a') as fh:
                fh.write("safety_checks: disabled\n")
            reload_config(prefix)
            assert context.safety_checks is SafetyChecks.disabled

            stdout, stderr, _ = run_command(Commands.INSTALL, prefix, '-c', 'conda-test', 'spiffy-test-app=0.5')
            assert message1 not in stderr
            assert message2 not in stderr
            assert package_is_installed(prefix, "spiffy-test-app=0.5")

    def test_json_create_install_update_remove(self):
        # regression test for #5384

        def assert_json_parsable(content):
            string = None
            try:
                for string in content and content.split('\0') or ():
                    json.loads(string)
            except Exception as e:
                log.warn(
                    "Problem parsing json output.\n"
                    "  content: %s\n"
                    "  string: %s\n"
                    "  error: %r",
                    content, string, e
                )
                raise

        try:
            prefix = make_temp_prefix(str(uuid4())[:7])

            stdout, stderr, _ = run_command(Commands.CREATE, prefix, "python=3.5", "--json", "--dry-run", use_exception_handler=True)
            assert_json_parsable(stdout)

            # regression test for #5825
            # contents of LINK and UNLINK is expected to have Dist format
            json_obj = json.loads(stdout)
            dist_dump = json_obj['actions']['LINK'][0]
            assert 'dist_name' in dist_dump

            stdout, stderr, _ = run_command(Commands.CREATE, prefix, "python=3.5", "--json")
            assert_json_parsable(stdout)
            assert not stderr
            json_obj = json.loads(stdout)
            dist_dump = json_obj['actions']['LINK'][0]
            assert 'dist_name' in dist_dump

            stdout, stderr, _ = run_command(Commands.INSTALL, prefix, 'flask=0.12', '--json')
            assert_json_parsable(stdout)
            assert not stderr
            assert package_is_installed(prefix, 'flask=0.12.2')
            assert package_is_installed(prefix, 'python=3')

            # Test force reinstall
            stdout, stderr, _ = run_command(Commands.INSTALL, prefix, '--force-reinstall', 'flask=0.12', '--json')
            assert_json_parsable(stdout)
            assert not stderr
            assert package_is_installed(prefix, 'flask=0.12.2')
            assert package_is_installed(prefix, 'python=3')

            stdout, stderr, _ = run_command(Commands.UPDATE, prefix, 'flask', '--json')
            assert_json_parsable(stdout)
            assert not stderr
            assert not package_is_installed(prefix, 'flask=0.12.2')
            assert package_is_installed(prefix, 'flask')
            assert package_is_installed(prefix, 'python=3')

            stdout, stderr, _ = run_command(Commands.REMOVE, prefix, 'flask', '--json')
            assert_json_parsable(stdout)
            assert not stderr
            assert not package_is_installed(prefix, 'flask=0.*')
            assert package_is_installed(prefix, 'python=3')

            # regression test for #5825
            # contents of LINK and UNLINK is expected to have Dist format
            json_obj = json.loads(stdout)
            dist_dump = json_obj['actions']['UNLINK'][0]
            assert 'dist_name' in dist_dump

            stdout, stderr, _ = run_command(Commands.LIST, prefix, '--revisions', '--json')
            assert not stderr
            json_obj = json.loads(stdout)
            assert len(json_obj) == 5
            assert json_obj[4]["rev"] == 4

            stdout, stderr, _ = run_command(Commands.INSTALL, prefix, '--revision', '0', '--json')
            assert_json_parsable(stdout)
            assert not stderr
            assert not package_is_installed(prefix, 'flask')
            assert package_is_installed(prefix, 'python=3')
        finally:
            rmtree(prefix, ignore_errors=True)

    def test_not_writable_env_raises_EnvironmentNotWritableError(self):
        with make_temp_env() as prefix:
            make_read_only(join(prefix, PREFIX_MAGIC_FILE))
            stdout, stderr, _ = run_command(Commands.INSTALL, prefix, "openssl", use_exception_handler=True)
            assert "EnvironmentNotWritableError" in stderr
            assert prefix in stderr

    def test_conda_update_package_not_installed(self):
        with make_temp_env() as prefix:
            with pytest.raises(PackageNotInstalledError):
                run_command(Commands.UPDATE, prefix, "sqlite", "openssl")

            with pytest.raises(CondaError) as conda_error:
                run_command(Commands.UPDATE, prefix, "conda-forge::*")
            assert conda_error.value.message.startswith("Invalid spec for 'conda update'")

    def test_noarch_python_package_with_entry_points(self):
        with make_temp_env("-c", "conda-test", "flask") as prefix:
            py_ver = get_python_version_for_prefix(prefix)
            sp_dir = get_python_site_packages_short_path(py_ver)
            py_file = sp_dir + "/flask/__init__.py"
            pyc_file = pyc_path(py_file, py_ver).replace('/', os.sep)
            assert isfile(join(prefix, py_file))
            assert isfile(join(prefix, pyc_file))
            exe_path = join(prefix, get_bin_directory_short_path(), 'flask')
            if on_win:
                exe_path += ".exe"
            assert isfile(exe_path)

            run_command(Commands.REMOVE, prefix, "flask")

            assert not isfile(join(prefix, py_file))
            assert not isfile(join(prefix, pyc_file))
            assert not isfile(exe_path)

    def test_noarch_python_package_without_entry_points(self):
        # regression test for #4546
        with make_temp_env("-c", "conda-test", "itsdangerous") as prefix:
            py_ver = get_python_version_for_prefix(prefix)
            sp_dir = get_python_site_packages_short_path(py_ver)
            py_file = sp_dir + "/itsdangerous.py"
            pyc_file = pyc_path(py_file, py_ver).replace('/', os.sep)
            assert isfile(join(prefix, py_file))
            assert isfile(join(prefix, pyc_file))

            run_command(Commands.REMOVE, prefix, "itsdangerous")

            assert not isfile(join(prefix, py_file))
            assert not isfile(join(prefix, pyc_file))

    def test_noarch_python_package_reinstall_on_pyver_change(self):
        with make_temp_env("-c", "conda-test", "itsdangerous=0.24", "python=3", use_restricted_unicode=on_win) as prefix:
            py_ver = get_python_version_for_prefix(prefix)
            assert py_ver.startswith('3')
            sp_dir = get_python_site_packages_short_path(py_ver)
            py_file = sp_dir + "/itsdangerous.py"
            pyc_file_py3 = pyc_path(py_file, py_ver).replace('/', os.sep)
            assert isfile(join(prefix, py_file))
            assert isfile(join(prefix, pyc_file_py3))

            run_command(Commands.INSTALL, prefix, "python=2")
            assert not isfile(join(prefix, pyc_file_py3))  # python3 pyc file should be gone

            py_ver = get_python_version_for_prefix(prefix)
            assert py_ver.startswith('2')
            sp_dir = get_python_site_packages_short_path(py_ver)
            py_file = sp_dir + "/itsdangerous.py"
            pyc_file_py2 = pyc_path(py_file, py_ver).replace('/', os.sep)

            assert isfile(join(prefix, py_file))
            assert isfile(join(prefix, pyc_file_py2))

    def test_noarch_generic_package(self):
        with make_temp_env("-c", "conda-test", "font-ttf-inconsolata") as prefix:
            assert isfile(join(prefix, 'fonts', 'Inconsolata-Regular.ttf'))

    def test_override_channels(self):
        with pytest.raises(OperationNotAllowed):
            with env_var('CONDA_OVERRIDE_CHANNELS_ENABLED', 'no', stack_callback=conda_tests_ctxt_mgmt_def_pol):
                with make_temp_env("--override-channels", "python") as prefix:
                    assert prefix

        with pytest.raises(CommandArgumentError):
            with make_temp_env("--override-channels", "python") as prefix:
                assert prefix

        stdout, stderr, _ = run_command(Commands.SEARCH, None, "--override-channels", "-c", "conda-test", "flask", "--json")
        assert not stderr
        assert len(json.loads(stdout)["flask"]) < 3
        assert json.loads(stdout)["flask"][0]["noarch"] == "python"

    def test_create_empty_env(self):
        with make_temp_env() as prefix:
            assert exists(join(prefix, 'conda-meta/history'))

            list_output = run_command(Commands.LIST, prefix)
            stdout = list_output[0]
            stderr = list_output[1]
            expected_output = """# packages in environment at %s:
#
# Name                    Version                   Build  Channel
""" % prefix
            self.assertEqual(stdout, expected_output)
            self.assertEqual(stderr, '')

            revision_output = run_command(Commands.LIST, prefix, '--revisions')
            stdout = revision_output[0]
            stderr = revision_output[1]
            assert stderr == ''
            self.assertIsInstance(stdout, string_types)

    @pytest.mark.skipif(reason="conda-forge doesn't have a full set of packages")
    def test_strict_channel_priority(self):
        with make_temp_env() as prefix:
            stdout, stderr, rc = run_command(
                Commands.CREATE, prefix,
                "-c", "conda-forge", "-c", "defaults", "python=3.6", "quaternion",
                "--strict-channel-priority", "--dry-run", "--json",
                use_exception_handler=True
            )
            assert not rc
            json_obj = json_loads(stdout)
            # We see:
            # libcxx             pkgs/main/osx-64::libcxx-4.0.1-h579ed51_0
            # Rather than spending more time looking for another package, just filter it out.
            # Same thing for Windows, this is because we use MKL always. Perhaps there's a
            # way to exclude it, I tried the "nomkl" package but that did not work.
            json_obj["actions"]["LINK"] = [link for link in json_obj["actions"]["LINK"]
                                           if link['name'] not in ('libcxx', 'libcxxabi', 'mkl', 'intel-openmp')]
            channel_groups = groupby("channel", json_obj["actions"]["LINK"])
            channel_groups = sorted(list(channel_groups))
            assert channel_groups == ["conda-forge",]

    def test_strict_resolve_get_reduced_index(self):
        channels = (Channel("defaults"),)
        specs = (MatchSpec("anaconda"),)
        index = get_reduced_index(None, channels, context.subdirs, specs, 'repodata.json')
        r = Resolve(index, channels=channels)
        with env_var("CONDA_CHANNEL_PRIORITY", "strict", stack_callback=conda_tests_ctxt_mgmt_def_pol):
            reduced_index = r.get_reduced_index(specs)
            channel_name_groups = {
                name: {prec.channel.name for prec in group}
                for name, group in iteritems(groupby("name", reduced_index))
            }
            channel_name_groups = {
                name: channel_names for name, channel_names in iteritems(channel_name_groups)
                if len(channel_names) > 1
            }
            assert {} == channel_name_groups

    def test_list_with_pip_no_binary(self):
        from conda.exports import rm_rf as _rm_rf
        # For this test to work on Windows, you can either pass use_restricted_unicode=on_win
        # to make_temp_env(), or you can set PYTHONUTF8 to 1 (and use Python 3.7 or above).
        # We elect to test the more complex of the two options.
        py_ver = "3.7"
        with make_temp_env("python="+py_ver, "pip") as prefix:
            evs = dict({"PYTHONUTF8": "1"})
            # This test does not activate the env.
            if on_win:
                evs['CONDA_DLL_SEARCH_MODIFICATION_ENABLE'] = '1'
            with env_vars(evs, stack_callback=conda_tests_ctxt_mgmt_def_pol):
                check_call(PYTHON_BINARY + " -m pip install --no-binary flask flask==0.10.1",
                           cwd=prefix, shell=True)
                PrefixData._cache_.clear()
                stdout, stderr, _ = run_command(Commands.LIST, prefix)
                stdout_lines = stdout.split('\n')
                assert any(line.endswith("pypi") for line in stdout_lines
                           if line.lower().startswith("flask"))

                # regression test for #5847
                #   when using rm_rf on a directory
                assert prefix in PrefixData._cache_
                _rm_rf(join(prefix, get_python_site_packages_short_path(py_ver)))
                assert prefix not in PrefixData._cache_

    def test_list_with_pip_wheel(self):
        from conda.exports import rm_rf as _rm_rf
        py_ver = "3.7"
        with make_temp_env("python="+py_ver, "pip") as prefix:
            evs = dict({"PYTHONUTF8": "1"})
            # This test does not activate the env.
            if on_win:
                evs['CONDA_DLL_SEARCH_MODIFICATION_ENABLE'] = '1'
            with env_vars(evs, stack_callback=conda_tests_ctxt_mgmt_def_pol):
                check_call(PYTHON_BINARY + " -m pip install flask==0.10.1",
                           cwd=prefix, shell=True)
                PrefixData._cache_.clear()
                stdout, stderr, _ = run_command(Commands.LIST, prefix)
                stdout_lines = stdout.split('\n')
                assert any(line.endswith("pypi") for line in stdout_lines
                           if line.lower().startswith("flask"))

                # regression test for #3433
                run_command(Commands.INSTALL, prefix, "python=3.5", no_capture=True)
                assert package_is_installed(prefix, 'python=3.5')

                # regression test for #5847
                #   when using rm_rf on a file
                assert prefix in PrefixData._cache_
                _rm_rf(join(prefix, get_python_site_packages_short_path("3.5")), "os.py")
                assert prefix not in PrefixData._cache_

        # regression test for #5980, related to #5847
        with make_temp_env() as prefix:
            assert isdir(prefix)
            assert prefix in PrefixData._cache_

            rmtree(prefix)
            assert not isdir(prefix)
            assert prefix in PrefixData._cache_

            _rm_rf(prefix)
            assert not isdir(prefix)
            assert prefix not in PrefixData._cache_

    def test_compare_success(self):
        with make_temp_env("python=3.6", "flask=1.0.2", "bzip2=1.0.8") as prefix:
            env_file = join(prefix, 'env.yml')
            touch(env_file)
            with open(env_file, "w") as f:
                f.write(
"""name: dummy
channels:
  - defaults
dependencies:
  - bzip2=1.0.8
  - flask>=1.0.1,<=1.0.4""")
            output, _, _ = run_command(Commands.COMPARE, prefix, env_file, "--json")
            assert "Success" in output
            rmtree(prefix, ignore_errors=True)

    def test_compare_fail(self):
        with make_temp_env("python=3.6", "flask=1.0.2", "bzip2=1.0.8") as prefix:
            env_file = join(prefix, 'env.yml')
            touch(env_file)
            with open(env_file, "w") as f:
                f.write(
"""name: dummy
channels:
  - defaults
dependencies:
  - yaml
  - flask=1.0.3""")
            output, _, _ = run_command(Commands.COMPARE, prefix, env_file, "--json")
            assert "yaml not found" in output
            assert "flask found but mismatch. Specification pkg: flask=1.0.3, Running pkg: flask==1.0.2=py36_1" in output
            rmtree(prefix, ignore_errors=True)

    def test_install_tarball_from_local_channel(self):
        # Regression test for #2812
        # install from local channel
        '''
        path = u'/private/var/folders/y1/ljv50nrs49gdqkrp01wy3_qm0000gn/T/pytest-of-rdonnelly/pytest-16/test_install_tarball_from_loca0/c352_çñßôêá'
        if on_win:
            path = u'C:\\çñ'
            percy = u'file:///C:/%C3%A7%C3%B1'
        else:
            path = u'/çñ'
            percy = 'file:///%C3%A7%C3%B1'

        url = path_to_url(path)
        assert url == percy
        path2 = url_to_path(url)
        assert path == path2
        assert type(path) == type(path2)
        # path_to_url("c:\\users\\est_install_tarball_from_loca0\a48a_6f154a82dbe3c7")
        '''
        with make_temp_env() as prefix, make_temp_channel(["flask-0.12.2"]) as channel:
            run_command(Commands.INSTALL, prefix, '-c', channel, 'flask=0.12.2', '--json')
            assert package_is_installed(prefix, channel + '::' + 'flask')
            flask_fname = [p for p in PrefixData(prefix).iter_records() if p['name'] == 'flask'][0]['fn']

            run_command(Commands.REMOVE, prefix, 'flask')
            assert not package_is_installed(prefix, 'flask=0')

            # Regression test for 2970
            # install from build channel as a tarball
            tar_path = join(PackageCacheData.first_writable().pkgs_dir, flask_fname)
            if not os.path.isfile(tar_path):
                tar_path = tar_path.replace('.conda', '.tar.bz2')
            conda_bld = join(dirname(PackageCacheData.first_writable().pkgs_dir), 'conda-bld')
            conda_bld_sub = join(conda_bld, context.subdir)
            if not isdir(conda_bld_sub):
                os.makedirs(conda_bld_sub)
            tar_bld_path = join(conda_bld_sub, basename(tar_path))
            copyfile(tar_path, tar_bld_path)
            run_command(Commands.INSTALL, prefix, tar_bld_path)
            assert package_is_installed(prefix, 'flask')

            # Regression test for #462
            with make_temp_env(tar_bld_path) as prefix2:
                assert package_is_installed(prefix2, 'flask')

    def test_tarball_install(self):
        with make_temp_env('bzip2') as prefix:
            # We have a problem. If bzip2 is extracted already but the tarball is missing then this fails.
            bzip2_data = [p for p in PrefixData(prefix).iter_records() if p['name'] == 'bzip2'][0]
            bzip2_fname = bzip2_data['fn']
            tar_old_path = join(PackageCacheData.first_writable().pkgs_dir, bzip2_fname)
            if not isfile(tar_old_path):
                log.warning("Installing bzip2 failed to save the compressed package, downloading it 'manually' ..")
                # Downloading to the package cache causes some internal inconsistency here:
                #
                #   File "/Users/rdonnelly/conda/conda/conda/common/path.py", line 72, in url_to_path
                #     raise CondaError("You can only turn absolute file: urls into paths (not %s)" % url)
                # conda.CondaError: You can only turn absolute file: urls into paths (not https://repo.anaconda.com/pkgs/main/osx-64/bzip2-1.0.6-h1de35cc_5.tar.bz2)
                #
                # .. so download to the root of the prefix instead.
                tar_old_path = join(prefix, bzip2_fname)
                from conda.gateways.connection.download import download
                download('https://repo.anaconda.com/pkgs/main/' + bzip2_data.subdir + '/' + bzip2_fname,
                         tar_old_path, None)
            assert isfile(tar_old_path), "Failed to cache:\n{}".format(tar_old_path)
            # It would be nice to be able to do this, but the cache folder name comes from
            # the file name and that is then all out of whack with the metadata.
            # tar_new_path = join(prefix, '家' + bzip2_fname)
            tar_new_path = join(prefix, bzip2_fname)

            run_command(Commands.RUN, prefix, cp_or_copy, tar_old_path, tar_new_path)
            assert isfile(tar_new_path), "Failed to copy:\n{}\nto:\n{}".format(tar_old_path, tar_new_path)
            run_command(Commands.INSTALL, prefix, tar_new_path)
            assert package_is_installed(prefix, 'bzip2')

    def test_tarball_install_and_bad_metadata(self):
        with make_temp_env("python=3.7.2", "flask=1.0.2", "--json") as prefix:
            assert package_is_installed(prefix, 'flask==1.0.2')
            flask_data = [p for p in PrefixData(prefix).iter_records() if p['name'] == 'flask'][0]
            run_command(Commands.REMOVE, prefix, 'flask')
            assert not package_is_installed(prefix, 'flask==1.0.2')
            assert package_is_installed(prefix, 'python')

            flask_fname = flask_data['fn']
            tar_old_path = join(PackageCacheData.first_writable().pkgs_dir, flask_fname)

            # if a .tar.bz2 is already in the file cache, it's fine.  Accept it or the .conda file here.
            if not isfile(tar_old_path):
                tar_old_path = tar_old_path.replace('.conda', '.tar.bz2')
            assert isfile(tar_old_path)

            with pytest.raises(DryRunExit):
                run_command(Commands.INSTALL, prefix, tar_old_path, "--dry-run")
                assert not package_is_installed(prefix, 'flask=1.*')

            # regression test for #2886 (part 1 of 2)
            # install tarball from package cache, default channel
            run_command(Commands.INSTALL, prefix, tar_old_path)
            assert package_is_installed(prefix, 'flask=1.*')

            # regression test for #2626
            # install tarball with full path, outside channel
            tar_new_path = join(prefix, flask_fname)
            copyfile(tar_old_path, tar_new_path)
            run_command(Commands.INSTALL, prefix, tar_new_path)
            assert package_is_installed(prefix, 'flask=1')

            # regression test for #2626
            # install tarball with relative path, outside channel
            run_command(Commands.REMOVE, prefix, 'flask')
            assert not package_is_installed(prefix, 'flask=1.0.2')
            tar_new_path = relpath(tar_new_path)
            run_command(Commands.INSTALL, prefix, tar_new_path)
            assert package_is_installed(prefix, 'flask=1')

            # regression test for #2886 (part 2 of 2)
            # install tarball from package cache, local channel
            run_command(Commands.REMOVE, prefix, 'flask', '--json')
            assert not package_is_installed(prefix, 'flask=1')
            run_command(Commands.INSTALL, prefix, tar_old_path)
            # The last install was from the `local::` channel
            assert package_is_installed(prefix, 'flask')

            # regression test for #2599
            # ignore json files in conda-meta that don't conform to name-version-build.json
            if not on_win:
                # xz is only a python dependency on unix
                xz_prec = next(PrefixData(prefix).query("xz"))
                dist_name = xz_prec.dist_str().split('::')[-1]
                xz_prefix_data_json_path = join(prefix, 'conda-meta', dist_name + '.json')
                copyfile(xz_prefix_data_json_path,
                         join(prefix, 'conda-meta', 'xz.json'))
                rm_rf(xz_prefix_data_json_path)
                assert not lexists(xz_prefix_data_json_path)
                PrefixData._cache_ = {}
                assert not package_is_installed(prefix, 'xz')

    @pytest.mark.skipif(on_win, reason="windows python doesn't depend on readline")
    def test_update_with_pinned_packages(self):
        # regression test for #6914
        with make_temp_env("-c", "https://repo.anaconda.com/pkgs/free", "python=2.7.12") as prefix:
            assert package_is_installed(prefix, "readline=6.2")
            # removing the history allows python to be updated too
            open(join(prefix, 'conda-meta', 'history'), 'w').close()
            PrefixData._cache_.clear()
            run_command(Commands.UPDATE, prefix, "readline", no_capture=True)
            assert package_is_installed(prefix, "readline")
            assert not package_is_installed(prefix, "readline=6.2")
            assert package_is_installed(prefix, "python=2.7")
            assert not package_is_installed(prefix, "python=2.7.12")

    def test_pinned_override_with_explicit_spec(self):
        with make_temp_env("python=3.6") as prefix:
            run_command(Commands.CONFIG, prefix,
                        "--add", "pinned_packages", "python=3.6.5")
            run_command(Commands.INSTALL, prefix, "python=3.7", no_capture=True)
            assert package_is_installed(prefix, "python=3.7")

    def test_remove_all(self):
        with make_temp_env("python") as prefix:
            assert exists(join(prefix, PYTHON_BINARY))
            assert package_is_installed(prefix, 'python')

            # regression test for #2154
            with pytest.raises(PackagesNotFoundError) as exc:
                run_command(Commands.REMOVE, prefix, 'python', 'foo', 'numpy')
            exception_string = repr(exc.value)
            assert "PackagesNotFoundError" in exception_string
            assert "- numpy" in exception_string
            assert "- foo" in exception_string

            run_command(Commands.REMOVE, prefix, '--all')
            assert path_is_clean(prefix)

    @pytest.mark.skipif(on_win, reason="windows usually doesn't support symlinks out-of-the box")
    @patch('conda.core.link.hardlink_supported', side_effect=lambda x, y: False)
    def test_allow_softlinks(self, hardlink_supported_mock):
        hardlink_supported_mock._result_cache.clear()
        with env_var("CONDA_ALLOW_SOFTLINKS", "true", stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with make_temp_env("pip") as prefix:
                assert islink(join(prefix, get_python_site_packages_short_path(
                    get_python_version_for_prefix(prefix)), 'pip', '__init__.py'))
        hardlink_supported_mock._result_cache.clear()

    @pytest.mark.skipif(on_win, reason="nomkl not present on windows")
    def test_remove_features(self):
        with make_temp_env("python=2", "numpy=1.13", "nomkl") as prefix:
            assert exists(join(prefix, PYTHON_BINARY))
            assert package_is_installed(prefix, 'numpy')
            assert package_is_installed(prefix, 'nomkl')
            assert not package_is_installed(prefix, 'mkl')

            # A consequence of discontinuing use of the 'features' key and instead
            # using direct dependencies is that removing the feature means that
            # packages associated with the track_features base package are completely removed
            # and not replaced with equivalent non-variant packages as before.
            run_command(Commands.REMOVE, prefix, '--features', 'nomkl')
            # assert package_is_installed(prefix, 'numpy')   # removed per above comment
            assert not package_is_installed(prefix, 'nomkl')
            # assert package_is_installed(prefix, 'mkl')  # removed per above comment

    @pytest.mark.skipif(on_win and context.bits == 32, reason="no 32-bit windows python on conda-forge")
    def test_dash_c_usage_replacing_python(self):
        # Regression test for #2606
        with make_temp_env("-c", "conda-forge", "python=3.7", no_capture=True) as prefix:
            assert exists(join(prefix, PYTHON_BINARY))
            assert package_is_installed(prefix, 'conda-forge::python=3.7')
            run_command(Commands.INSTALL, prefix, "decorator")
            assert package_is_installed(prefix, 'conda-forge::python=3.7')

            with make_temp_env('--clone', prefix) as clone_prefix:
                assert package_is_installed(clone_prefix, 'conda-forge::python=3.7')
                assert package_is_installed(clone_prefix, "decorator")

            # Regression test for #2645
            fn = glob(join(prefix, 'conda-meta', 'python-3.7*.json'))[-1]
            with open(fn) as f:
                data = json.load(f)
            for field in ('url', 'channel', 'schannel'):
                if field in data:
                    del data[field]
            with open(fn, 'w') as f:
                json.dump(data, f)
            PrefixData._cache_ = {}

            with make_temp_env('-c', 'conda-forge', '--clone', prefix) as clone_prefix:
                assert package_is_installed(clone_prefix, 'python=3.7')
                assert package_is_installed(clone_prefix, 'decorator')

    def test_install_prune_flag(self):
        with make_temp_env("python=3", "flask") as prefix:
            assert package_is_installed(prefix, 'flask')
            assert package_is_installed(prefix, 'python=3')
            run_command(Commands.REMOVE, prefix, "flask")
            assert not package_is_installed(prefix, 'flask')
            # this should get pruned when flask is removed
            assert not package_is_installed(prefix, 'itsdangerous')
            assert package_is_installed(prefix, 'python=3')

    @pytest.mark.skipif(on_win, reason="readline is only a python dependency on unix")
    def test_remove_force_remove_flag(self):
        with make_temp_env("python") as prefix:
            assert package_is_installed(prefix, 'readline')
            assert package_is_installed(prefix, 'python')

            run_command(Commands.REMOVE, prefix, 'readline', '--force-remove')
            assert not package_is_installed(prefix, 'readline')
            assert package_is_installed(prefix, 'python')

    def test_install_force_reinstall_flag(self):
        with make_temp_env("python") as prefix:
            stdout, stderr, _ = run_command(Commands.INSTALL, prefix,
                                         "--json", "--dry-run", "--force-reinstall", "python",
                                         use_exception_handler=True)
            output_obj = json.loads(stdout.strip())
            unlink_actions = output_obj['actions']['UNLINK']
            link_actions = output_obj['actions']['LINK']
            assert len(unlink_actions) == len(link_actions) == 1
            assert unlink_actions[0] == link_actions[0]
            assert unlink_actions[0]['name'] == 'python'

    def test_create_no_deps_flag(self):
        with make_temp_env("python=2", "flask", "--no-deps") as prefix:
            assert package_is_installed(prefix, 'flask')
            assert package_is_installed(prefix, 'python=2')
            assert not package_is_installed(prefix, 'openssl')
            assert not package_is_installed(prefix, 'itsdangerous')

    def test_create_only_deps_flag(self):
        with make_temp_env("python=2", "flask", "--only-deps", no_capture=True) as prefix:
            assert not package_is_installed(prefix, 'flask')
            assert package_is_installed(prefix, 'python')
            if not on_win:
                # sqlite is a dependency of Python on all platforms
                assert package_is_installed(prefix, 'sqlite')
            assert package_is_installed(prefix, 'itsdangerous')

            # test that a later install keeps the --only-deps packages around
            run_command(Commands.INSTALL, prefix, "imagesize", no_capture=True)
            assert package_is_installed(prefix, 'itsdangerous')
            assert not package_is_installed(prefix, 'flask')

            # test that --only-deps installed stuff survives updates of unrelated packages
            run_command(Commands.UPDATE, prefix, "imagesize", no_capture=True)
            assert package_is_installed(prefix, 'itsdangerous')
            assert not package_is_installed(prefix, 'flask')

            # test that --only-deps installed stuff survives removal of unrelated packages
            run_command(Commands.REMOVE, prefix, "imagesize", no_capture=True)
            assert package_is_installed(prefix, 'itsdangerous')
            assert not package_is_installed(prefix, 'flask')

    def test_install_update_deps_flag(self):
        with make_temp_env("flask=2.0.1", "jinja2=3.0.1") as prefix:
            python = join(prefix, PYTHON_BINARY)
            result_before = subprocess_call_with_clean_env([python, "--version"])
            assert package_is_installed(prefix, "flask=2.0.1")
            assert package_is_installed(prefix, "jinja2=3.0.1")
            run_command(Commands.INSTALL, prefix, "flask", "--update-deps")
            result_after = subprocess_call_with_clean_env([python, "--version"])
            assert result_before == result_after
            assert package_is_installed(prefix, "flask>2.0.1")
            assert package_is_installed(prefix, "jinja2>3.0.1")

    def test_install_only_deps_flag(self):
        with make_temp_env("flask=2.0.2", "jinja2=3.0.2") as prefix:
            python = join(prefix, PYTHON_BINARY)
            result_before = subprocess_call_with_clean_env([python, "--version"])
            assert package_is_installed(prefix, "flask=2.0.2")
            assert package_is_installed(prefix, "jinja2=3.0.2")
            run_command(Commands.INSTALL, prefix, "flask", "--only-deps")
            result_after = subprocess_call_with_clean_env([python, "--version"])
            assert result_before == result_after
            assert package_is_installed(prefix, "flask=2.0.2")
            assert package_is_installed(prefix, "jinja2=3.0.2")

        with make_temp_env("flask==2.0.2", "--only-deps") as prefix:
            assert not package_is_installed(prefix, "flask")

    def test_install_update_deps_only_deps_flags(self):
        with make_temp_env("flask=2.0.1", "jinja2=3.0.1") as prefix:
            python = join(prefix, PYTHON_BINARY)
            result_before = subprocess_call_with_clean_env([python, "--version"])
            assert package_is_installed(prefix, "flask=2.0.1")
            assert package_is_installed(prefix, "jinja2=3.0.1")
            run_command(Commands.INSTALL, prefix, "flask", "python", "--update-deps", "--only-deps")
            result_after = subprocess_call_with_clean_env([python, "--version"])
            assert result_before == result_after
            assert package_is_installed(prefix, "flask=2.0.1")
            assert package_is_installed(prefix, "jinja2>3.0.1")


    @pytest.mark.xfail(on_win, reason="nomkl not present on windows",
                       strict=True)
    def test_install_features(self):
        with make_temp_env("python=2", "numpy=1.13", "nomkl", no_capture=True) as prefix:
            assert package_is_installed(prefix, "numpy")
            assert package_is_installed(prefix, "nomkl")
            assert not package_is_installed(prefix, "mkl")

        with make_temp_env("python=2", "numpy=1.13") as prefix:
            assert package_is_installed(prefix, "numpy")
            assert not package_is_installed(prefix, "nomkl")
            assert package_is_installed(prefix, "mkl")

            run_command(Commands.INSTALL, prefix, "nomkl", no_capture=True)
            assert package_is_installed(prefix, "numpy")
            assert package_is_installed(prefix, "nomkl")
            assert package_is_installed(prefix, "blas=1.0=openblas")
            assert not package_is_installed(prefix, "mkl_fft")
            assert not package_is_installed(prefix, "mkl_random")
            # assert not package_is_installed(prefix, "mkl")  # pruned as an indirect dep

    def test_clone_offline_simple(self):
        with make_temp_env("bzip2") as prefix:
            assert package_is_installed(prefix, 'bzip2')

            with make_temp_env('--clone', prefix, '--offline') as clone_prefix:
                assert context.offline
                assert package_is_installed(clone_prefix, 'bzip2')

    def test_conda_config_describe(self):
        with make_temp_env() as prefix:
            stdout, stderr, _ = run_command(Commands.CONFIG, prefix, "--describe")
            assert not stderr
            skip_categories = ('CLI-only', 'Hidden and Undocumented')
            documented_parameter_names = chain.from_iterable((
                parameter_names for category, parameter_names in iteritems(context.category_map)
                if category not in skip_categories
            ))

            for param_name in documented_parameter_names:
                assert re.search(r'^# # %s \(' % param_name, stdout, re.MULTILINE), param_name

            stdout, stderr, _ = run_command(Commands.CONFIG, prefix, "--describe", "--json")
            assert not stderr
            json_obj = json.loads(stdout.strip())
            assert len(json_obj) >= 55
            assert 'description' in json_obj[0]

            with env_var('CONDA_QUIET', 'yes', stack_callback=conda_tests_ctxt_mgmt_def_pol):
                stdout, stderr, _ = run_command(Commands.CONFIG, prefix, "--show-sources")
                assert not stderr
                assert 'envvars' in stdout.strip()

                stdout, stderr, _ = run_command(Commands.CONFIG, prefix, "--show-sources", "--json")
                assert not stderr
                json_obj = json.loads(stdout.strip())
                assert "quiet" in json_obj['envvars'] and json_obj['envvars']["quiet"] == True
                assert json_obj['cmd_line'] == {'json': True}

            run_command(Commands.CONFIG, prefix, "--set", "changeps1", "false")
            with pytest.raises(CondaError):
                run_command(Commands.CONFIG, prefix, "--write-default")

            rm_rf(join(prefix, 'condarc'))
            run_command(Commands.CONFIG, prefix, "--write-default")

            with open(join(prefix, 'condarc')) as fh:
                data = fh.read()

            for param_name in documented_parameter_names:
                assert re.search(r'^# %s \(' % param_name, data, re.MULTILINE), param_name

            stdout, stderr, _ = run_command(Commands.CONFIG, prefix, "--describe", "--json")
            assert not stderr
            json_obj = json.loads(stdout.strip())
            assert len(json_obj) >= 42
            assert 'description' in json_obj[0]

            with env_var('CONDA_QUIET', 'yes', stack_callback=conda_tests_ctxt_mgmt_def_pol):
                stdout, stderr, _ = run_command(Commands.CONFIG, prefix, "--show-sources")
                assert not stderr
                assert 'envvars' in stdout.strip()

                stdout, stderr, _ = run_command(Commands.CONFIG, prefix, "--show-sources", "--json")
                assert not stderr
                json_obj = json.loads(stdout.strip())
                assert "quiet" in json_obj['envvars'] and json_obj['envvars']["quiet"] == True
                assert json_obj['cmd_line'] == {'json': True}

    def test_conda_config_validate(self):
        with make_temp_env() as prefix:
            run_command(Commands.CONFIG, prefix, "--set", "ssl_verify", "no")
            stdout, stderr, _ = run_command(Commands.CONFIG, prefix, "--validate")
            assert not stdout
            assert not stderr

            try:
                with open(join(prefix, 'condarc'), 'w') as fh:
                    fh.write('default_python: anaconda\n')
                    fh.write('ssl_verify: /path/doesnt/exist\n')
                reload_config(prefix)

                with pytest.raises(CondaMultiError) as exc:
                    run_command(Commands.CONFIG, prefix, "--validate")

                assert len(exc.value.errors) == 2
                str_exc_value = str(exc.value)
                assert str("must be a boolean, a path to a certificate bundle file, or a path to a directory containing certificates of trusted CAs") in str_exc_value
                assert str("default_python value 'anaconda' not of the form '[23].[0-9][0-9]?'") in str_exc_value
            finally:
                reset_context()

    def test_rpy_search(self):
        with make_temp_env("python=3.5") as prefix:
            run_command(Commands.CONFIG, prefix, "--add", "channels", "https://repo.anaconda.com/pkgs/free")
            run_command(Commands.CONFIG, prefix, "--remove", "channels", "defaults")
            stdout, stderr, _ = run_command(Commands.CONFIG, prefix, "--show", "--json")
            json_obj = json_loads(stdout)
            assert 'defaults' not in json_obj['channels']

            assert package_is_installed(prefix, 'python')
            assert 'r' not in context.channels

            # assert conda search cannot find rpy2
            stdout, stderr, _ = run_command(Commands.SEARCH, prefix, "rpy2", "--json", use_exception_handler=True)
            json_obj = json_loads(stdout.replace("Fetching package metadata ...", "").strip())
            assert json_obj['exception_name'] == 'PackagesNotFoundError'

            # add r channel
            run_command(Commands.CONFIG, prefix, "--add", "channels", "r")
            stdout, stderr, _ = run_command(Commands.CONFIG, prefix, "--show", "--json")
            json_obj = json_loads(stdout)
            assert 'r' in json_obj['channels']

            # assert conda search can now find rpy2
            stdout, stderr, _ = run_command(Commands.SEARCH, prefix, "rpy2", "--json")
            json_obj = json_loads(stdout.replace("Fetching package metadata ...", "").strip())


    def _test_compile_pyc(self, use_sys_python=False, use_dll_search_modifiction=False):
        evs = {}
        if use_dll_search_modifiction:
            evs['CONDA_DLL_SEARCH_MODIFICATION_ENABLE'] = '1'
        with env_vars(evs, stack_callback=conda_tests_ctxt_mgmt_def_pol):
            packages = []
            if use_sys_python:
                py_ver = '{}.{}'.format(sys.version_info[0], sys.version_info[1])
            else:
                # We force the use of 'the other' Python on Windows so that Windows
                # runtime / DLL incompatibilities will be readily apparent.
                py_ver = '3.7' if sys.version_info[0] == 3 else '2.7'
                packages.append('python=' + py_ver)
            with make_temp_env(*packages, use_restricted_unicode=True
                               if py_ver.startswith('2') else False) as prefix:
                if use_sys_python:
                    python_binary = sys.executable
                else:
                    python_binary = join(prefix, 'python.exe' if on_win else 'bin/python')
                assert os.path.isfile(python_binary), "Cannot even find Python"
                spdir = join('Lib', 'site-packages') if on_win else join('lib', 'python', py_ver)
                # Bad pun on itsdangerous.
                py_full_paths = (join(prefix, spdir, 'isitsafe.py'),)
                pyc_full_paths = [pyc_path(py_path, py_ver) for py_path in py_full_paths]
                from os import makedirs
                try:
                    makedirs(dirname(py_full_paths[0]))
                except:
                    pass
                try:
                    makedirs(dirname(pyc_full_paths[0]))
                except:
                    pass
                with open(py_full_paths[0], 'w') as fpy:
                    fpy.write("__version__ = 1.0")
                    fpy.close()
                from conda.gateways.disk.create import compile_multiple_pyc
                compile_multiple_pyc(python_binary, py_full_paths, pyc_full_paths, prefix, py_ver)
                assert isfile(pyc_full_paths[0]), "Failed to generate expected .pyc file {}".format(pyc_full_paths[0])


    def test_compile_pyc_sys_python(self):
        return self._test_compile_pyc(use_sys_python=True)

    def test_compile_pyc_new_python(self):
        return self._test_compile_pyc(use_sys_python=False)

    def test_conda_run_1(self):
        with make_temp_env(use_restricted_unicode=False, name=str(uuid4())[:7]) as prefix:
            output, error, rc = run_command(Commands.RUN, prefix, 'echo', 'hello')
            assert output == 'hello' + os.linesep
            assert not error
            assert rc == 0
            output, error, rc = run_command(Commands.RUN, prefix, 'exit', '5')
            assert not output
            assert not error
            assert rc == 5

    def test_conda_run_nonexistant_prefix(self):
        with make_temp_env(use_restricted_unicode=False, name=str(uuid4())[:7]) as prefix:
            prefix = join(prefix, "clearly_a_prefix_that_does_not_exist")
            with pytest.raises(EnvironmentLocationNotFound):
                output, error, rc = run_command(Commands.RUN, prefix, 'echo', 'hello')

    def test_conda_run_prefix_not_a_conda_env(self):
        with tempdir() as prefix:
            with pytest.raises(DirectoryNotACondaEnvironmentError):
                output, error, rc = run_command(Commands.RUN, prefix, 'echo', 'hello')


    def test_clone_offline_multichannel_with_untracked(self):
        with env_vars({
            "CONDA_DLL_SEARCH_MODIFICATION_ENABLE": "1",
        }, stack_callback=conda_tests_ctxt_mgmt_def_pol):
            # The flask install will use this version of Python. That is then used to compile flask's pycs.
            flask_python = '3.6'
            with make_temp_env("python=3.7", use_restricted_unicode=True) as prefix:

                run_command(Commands.CONFIG, prefix, "--add", "channels", "https://repo.anaconda.com/pkgs/free")
                run_command(Commands.CONFIG, prefix, "--remove", "channels", "defaults")

                run_command(Commands.INSTALL, prefix, "-c", "conda-test", "flask", "python=" + flask_python)

                touch(join(prefix, 'test.file'))  # untracked file
                with make_temp_env("--clone", prefix, "--offline") as clone_prefix:
                    assert context.offline
                    assert package_is_installed(clone_prefix, "python=" + flask_python)
                    assert package_is_installed(clone_prefix, "flask=0.11.1=py_0")
                    assert isfile(join(clone_prefix, 'test.file'))  # untracked file

    def test_package_pinning(self):
        with make_temp_env("python=2.7", "itsdangerous=0.24", "pytz=2017.3", no_capture=True) as prefix:
            assert package_is_installed(prefix, "itsdangerous=0.24")
            assert package_is_installed(prefix, "python=2.7")
            assert package_is_installed(prefix, "pytz=2017.3")

            with open(join(prefix, 'conda-meta', 'pinned'), 'w') as fh:
                fh.write("itsdangerous 0.24\n")

            run_command(Commands.UPDATE, prefix, "--all", no_capture=True)
            assert package_is_installed(prefix, "itsdangerous=0.24")
            # assert not package_is_installed(prefix, "python=3.5")  # should be python-3.6, but it's not because of add_defaults_to_specs
            assert package_is_installed(prefix, "python=2.7")
            assert not package_is_installed(prefix, "pytz=2017.3")
            assert package_is_installed(prefix, "pytz")

            run_command(Commands.UPDATE, prefix, "--all", "--no-pin", no_capture=True)
            assert package_is_installed(prefix, "python=2.7")
            assert not package_is_installed(prefix, "itsdangerous=0.24")

    def test_update_all_updates_pip_pkg(self):
        with make_temp_env("python=3.6", "pip", "pytz=2018", no_capture=True) as prefix:
            pip_ioo, pip_ioe, _ = run_command(Commands.CONFIG, prefix, "--set", "pip_interop_enabled", "true")

            pip_o, pip_e, _ = run_command(Commands.RUN, prefix, "--dev", "python", "-m", "pip", "install", "itsdangerous==0.24")
            PrefixData._cache_.clear()
            stdout, stderr, _ = run_command(Commands.LIST, prefix, "--json")
            assert not stderr
            json_obj = json.loads(stdout)
            six_info = next(info for info in json_obj if info["name"] == "itsdangerous")
            assert six_info == {
                "base_url": "https://conda.anaconda.org/pypi",
                "build_number": 0,
                "build_string": "pypi_0",
                "channel": "pypi",
                "dist_name": "itsdangerous-0.24-pypi_0",
                "name": "itsdangerous",
                "platform": "pypi",
                "version": "0.24",
            }
            assert package_is_installed(prefix, "itsdangerous=0.24")

            run_command(Commands.UPDATE, prefix, "--all")
            assert package_is_installed(prefix, "itsdangerous>0.24")
            assert package_is_installed(prefix, "pytz>2018")

    def test_package_optional_pinning(self):
        with make_temp_env() as prefix:
            run_command(Commands.CONFIG, prefix,
                        "--add", "pinned_packages", "python=3.6.5")
            run_command(Commands.INSTALL, prefix, "openssl")
            assert not package_is_installed(prefix, "python")
            run_command(Commands.INSTALL, prefix, "flask")
            assert package_is_installed(prefix, "python=3.6.5")

    def test_update_deps_flag_absent(self):
        with make_temp_env("python=2", "itsdangerous=0.24") as prefix:
            assert package_is_installed(prefix, 'python=2')
            assert package_is_installed(prefix, 'itsdangerous=0.24')
            assert not package_is_installed(prefix, 'flask')

            run_command(Commands.INSTALL, prefix, 'flask')
            assert package_is_installed(prefix, 'python=2')
            assert package_is_installed(prefix, 'itsdangerous=0.24')
            assert package_is_installed(prefix, 'flask')

    def test_update_deps_flag_present(self):
        with make_temp_env("python=2", "itsdangerous=0.24") as prefix:
            assert package_is_installed(prefix, 'python=2')
            assert package_is_installed(prefix, 'itsdangerous=0.24')
            assert not package_is_installed(prefix, 'flask')

            run_command(Commands.INSTALL, prefix, '--update-deps', 'python=2', 'flask')
            assert package_is_installed(prefix, 'python=2')
            assert not package_is_installed(prefix, 'itsdangerous=0.24')
            assert package_is_installed(prefix, 'itsdangerous')
            assert package_is_installed(prefix, 'flask')

    @pytest.mark.skipif(True, reason="Add this test back someday.")
    # @pytest.mark.skipif(not on_win, reason="shortcuts only relevant on Windows")
    def test_shortcut_in_underscore_env_shows_message(self):
        prefix = make_temp_prefix("_" + str(uuid4())[:7])
        with make_temp_env(prefix=prefix):
            stdout, stderr, _ = run_command(Commands.INSTALL, prefix, "console_shortcut")
            assert ("Environment name starts with underscore '_'.  "
                    "Skipping menu installation." in stderr)

    @pytest.mark.skipif(not on_win, reason="shortcuts only relevant on Windows")
    def test_shortcut_not_attempted_with_no_shortcuts_arg(self):
        prefix = make_temp_prefix("_" + str(uuid4())[:7])
        shortcut_dir = get_shortcut_dir()
        shortcut_file = join(shortcut_dir, "Anaconda Prompt ({0}).lnk".format(basename(prefix)))
        with make_temp_env(prefix=prefix):
            stdout, stderr, _ = run_command(Commands.INSTALL, prefix, "console_shortcut",
                                         "--no-shortcuts")
            assert ("Environment name starts with underscore '_'.  Skipping menu installation."
                    not in stderr)
            assert not isfile(shortcut_file)

    @pytest.mark.skipif(not on_win, reason="shortcuts only relevant on Windows")
    def test_shortcut_creation_installs_shortcut(self):
        shortcut_dir = get_shortcut_dir()
        shortcut_dir = join(shortcut_dir, "Anaconda{0} ({1}-bit)"
                                          "".format(sys.version_info.major, context.bits))

        prefix = make_temp_prefix(str(uuid4())[:7])
        shortcut_file = join(shortcut_dir, "Anaconda Prompt ({0}).lnk".format(basename(prefix)))
        try:
            with make_temp_env("console_shortcut", prefix=prefix):
                assert package_is_installed(prefix, 'console_shortcut')
                assert isfile(shortcut_file), ("Shortcut not found in menu dir. "
                                               "Contents of dir:\n"
                                               "{0}".format(os.listdir(shortcut_dir)))

                # make sure that cleanup without specifying --shortcuts still removes shortcuts
                run_command(Commands.REMOVE, prefix, 'console_shortcut')
                assert not package_is_installed(prefix, 'console_shortcut')
                assert not isfile(shortcut_file)
        finally:
            rmtree(prefix, ignore_errors=True)
            if isfile(shortcut_file):
                os.remove(shortcut_file)

    @pytest.mark.skipif(not on_win, reason="shortcuts only relevant on Windows")
    def test_shortcut_absent_does_not_barf_on_uninstall(self):
        shortcut_dir = get_shortcut_dir()
        shortcut_dir = join(shortcut_dir, "Anaconda{0} ({1}-bit)"
                                          "".format(sys.version_info.major, context.bits))

        prefix = make_temp_prefix(str(uuid4())[:7])
        shortcut_file = join(shortcut_dir, "Anaconda Prompt ({0}).lnk".format(basename(prefix)))
        assert not isfile(shortcut_file)

        try:
            # including --no-shortcuts should not get shortcuts installed
            with make_temp_env("console_shortcut", "--no-shortcuts", prefix=prefix):
                assert package_is_installed(prefix, 'console_shortcut')
                assert not isfile(shortcut_file)

                # make sure that cleanup without specifying --shortcuts still removes shortcuts
                run_command(Commands.REMOVE, prefix, 'console_shortcut')
                assert not package_is_installed(prefix, 'console_shortcut')
                assert not isfile(shortcut_file)
        finally:
            rmtree(prefix, ignore_errors=True)
            if isfile(shortcut_file):
                os.remove(shortcut_file)

    @pytest.mark.skipif(not on_win, reason="shortcuts only relevant on Windows")
    def test_shortcut_absent_when_condarc_set(self):
        shortcut_dir = get_shortcut_dir()
        shortcut_dir = join(shortcut_dir, "Anaconda{0} ({1}-bit)"
                                          "".format(sys.version_info.major, context.bits))

        prefix = make_temp_prefix(str(uuid4())[:7])
        shortcut_file = join(shortcut_dir, "Anaconda Prompt ({0}).lnk".format(basename(prefix)))
        assert not isfile(shortcut_file)

        # set condarc shortcuts: False
        run_command(Commands.CONFIG, prefix, "--set", "shortcuts", "false")
        stdout, stderr, _ = run_command(Commands.CONFIG, prefix, "--get", "--json")
        json_obj = json_loads(stdout)
        assert json_obj['rc_path'] == join(prefix, 'condarc')
        assert json_obj['get']['shortcuts'] is False

        try:
            with make_temp_env("console_shortcut", prefix=prefix):
                # including shortcuts: False from condarc should not get shortcuts installed
                assert package_is_installed(prefix, 'console_shortcut')
                assert not isfile(shortcut_file)

                # make sure that cleanup without specifying --shortcuts still removes shortcuts
                run_command(Commands.REMOVE, prefix, 'console_shortcut')
                assert not package_is_installed(prefix, 'console_shortcut')
                assert not isfile(shortcut_file)
        finally:
            rmtree(prefix, ignore_errors=True)
            if isfile(shortcut_file):
                os.remove(shortcut_file)

    def test_create_default_packages(self):
        # Regression test for #3453
        try:
            prefix = make_temp_prefix(str(uuid4())[:7])

            # set packages
            run_command(Commands.CONFIG, prefix, "--add", "create_default_packages", "pip")
            run_command(Commands.CONFIG, prefix, "--add", "create_default_packages", "flask")
            stdout, stderr, _ = run_command(Commands.CONFIG, prefix, "--show")
            yml_obj = yaml_round_trip_load(stdout)
            assert yml_obj['create_default_packages'] == ['flask', 'pip']

            assert not package_is_installed(prefix, 'python=2')
            assert not package_is_installed(prefix, 'pytz')
            assert not package_is_installed(prefix, 'flask')

            with make_temp_env("python=2", "pytz", prefix=prefix):
                assert package_is_installed(prefix, 'python=2')
                assert package_is_installed(prefix, 'pytz')
                assert package_is_installed(prefix, 'flask')

        finally:
            rmtree(prefix, ignore_errors=True)

    def test_create_default_packages_no_default_packages(self):
        try:
            prefix = make_temp_prefix(str(uuid4())[:7])

            # set packages
            run_command(Commands.CONFIG, prefix, "--add", "create_default_packages", "pip")
            run_command(Commands.CONFIG, prefix, "--add", "create_default_packages", "flask")
            stdout, stderr, _ = run_command(Commands.CONFIG, prefix, "--show")
            yml_obj = yaml_round_trip_load(stdout)
            assert yml_obj['create_default_packages'] == ['flask', 'pip']

            assert not package_is_installed(prefix, 'python=2')
            assert not package_is_installed(prefix, 'pytz')
            assert not package_is_installed(prefix, 'flask')

            with make_temp_env("python=2", "pytz", "--no-default-packages", prefix=prefix):
                assert package_is_installed(prefix, 'python=2')
                assert package_is_installed(prefix, 'pytz')
                assert not package_is_installed(prefix, 'flask')

        finally:
            rmtree(prefix, ignore_errors=True)

    def test_create_dry_run(self):
        # Regression test for #3453
        prefix = '/some/place'
        with pytest.raises(DryRunExit):
            run_command(Commands.CREATE, prefix, "--dry-run")
        output, _, _ = run_command(Commands.CREATE, prefix, "--dry-run", use_exception_handler=True)
        assert join('some', 'place') in output
        # TODO: This assert passes locally but fails on CI boxes; figure out why and re-enable
        # assert "The following empty environments will be CREATED" in stdout

        prefix = '/another/place'
        with pytest.raises(DryRunExit):
            run_command(Commands.CREATE, prefix, "flask", "--dry-run")
        output, _, _ = run_command(Commands.CREATE, prefix, "flask", "--dry-run", use_exception_handler=True)
        assert ":flask" in output
        assert ":python" in output
        assert join('another', 'place') in output

    def test_create_dry_run_json(self):
        prefix = '/some/place'
        with pytest.raises(DryRunExit):
            run_command(Commands.CREATE, prefix, "flask", "--dry-run", "--json")
        output, _, _ = run_command(Commands.CREATE, prefix, "flask", "--dry-run", "--json", use_exception_handler=True)
        loaded = json.loads(output)
        names = set(d['name'] for d in loaded['actions']['LINK'])
        assert "python" in names
        assert "flask" in names

    def test_create_dry_run_yes_safety(self):
        with make_temp_env() as prefix:
            with pytest.raises(CondaValueError):
                run_command(Commands.CREATE, prefix, "--dry-run", "--yes")
            assert exists(prefix)

    def test_packages_not_found(self):
        with make_temp_env() as prefix:
            with pytest.raises(PackagesNotFoundError) as exc:
                run_command(Commands.INSTALL, prefix, "not-a-real-package")
            assert "not-a-real-package" in text_type(exc.value)

            _, error, _ = run_command(Commands.INSTALL, prefix, "not-a-real-package",
                                   use_exception_handler=True)
            assert "not-a-real-package" in error

    def test_conda_pip_interop_dependency_satisfied_by_pip(self):
        with make_temp_env("python=3.7", "pip", use_restricted_unicode=False) as prefix:
            pip_ioo, pip_ioe, _ = run_command(Commands.CONFIG, prefix, "--set", "pip_interop_enabled", "true")
            pip_o, pip_e, _ = run_command(Commands.RUN, prefix, "--dev", "python", "-m", "pip", "install", "itsdangerous")

            PrefixData._cache_.clear()
            output, error, _ = run_command(Commands.LIST, prefix)
            assert 'itsdangerous' in output
            assert not error

            output, _, _ = run_command(Commands.INSTALL, prefix, 'flask', '--dry-run', '--json',
                                       use_exception_handler=True)
            json_obj = json.loads(output)
            print(json_obj)
            # itsdangerous shouldn't be in this list, because it's already present and satisfied
            #     by the pip package
            assert any(rec["name"] == "flask" for rec in json_obj["actions"]["LINK"])
            assert not any(rec["name"] == "itsdangerous" for rec in json_obj["actions"]["LINK"])

            output, error, _ = run_command(Commands.SEARCH, prefix, "not-a-real-package", "--json",
                                           use_exception_handler=True)
            assert not error
            json_obj = json_loads(output.strip())
            assert json_obj['exception_name'] == 'PackagesNotFoundError'
            assert not len(json_obj.keys()) == 0

    @pytest.mark.skipif(context.subdir == "win-32", reason="metadata is wrong; give python2.7")
    def test_conda_pip_interop_pip_clobbers_conda(self):
        # 1. conda install old six
        # 2. pip install -U six
        # 3. conda list shows new six and deletes old conda record
        # 4. probably need to purge something with the history file too?
        # Python 3.5 and PIP are not unicode-happy on Windows:
        #   File "C:\Users\builder\AppData\Local\Temp\f903_固ō한ñђáγßê家ôç_35\lib\site-packages\pip\_vendor\urllib3\util\ssl_.py", line 313, in ssl_wrap_socket
        #     context.load_verify_locations(ca_certs, ca_cert_dir)
        #   TypeError: cafile should be a valid filesystem path
        with make_temp_env("-c", "https://repo.anaconda.com/pkgs/free", "six=1.9", "pip=9.0.3", "python=3.5",
                           use_restricted_unicode=on_win) as prefix:
            run_command(Commands.CONFIG, prefix, "--set", "pip_interop_enabled", "true")
            assert package_is_installed(prefix, "six=1.9.0")
            assert package_is_installed(prefix, "python=3.5")

            # On Windows, it's more than prefix.lower(), we get differently shortened paths too.
            # If only we could use pathlib.
            if not on_win:
                output, _, _ = run_command(Commands.RUN, prefix, which_or_where, "python")
                assert prefix.lower() in output.lower(), \
                                         "We should be running python in {}\n" \
                                         "We are running {}\n" \
                                         "Please check the CONDA_PREFIX PATH promotion in tests/__init__.py\n" \
                                         "for a likely place to add more fixes".format(prefix, output)
            output, _, _ = run_command(Commands.RUN, prefix, "python", "-m", "pip", "freeze")
            pkgs = set(ensure_text_type(v.strip()) for v in output.splitlines() if v.strip())
            assert "six==1.9.0" in pkgs

            py_ver = get_python_version_for_prefix(prefix)
            sp_dir = get_python_site_packages_short_path(py_ver)

            output, _, _ = run_command(Commands.RUN, prefix, "python", "-m", "pip", "install", "-U", "six==1.10")
            assert "Successfully installed six-1.10.0" in ensure_text_type(output)
            PrefixData._cache_.clear()
            stdout, stderr, _ = run_command(Commands.LIST, prefix, "--json")
            assert not stderr
            json_obj = json.loads(stdout)
            six_info = next(info for info in json_obj if info["name"] == "six")
            assert six_info == {
                "base_url": "https://conda.anaconda.org/pypi",
                "build_number": 0,
                "build_string": "pypi_0",
                "channel": "pypi",
                "dist_name": "six-1.10.0-pypi_0",
                "name": "six",
                "platform": "pypi",
                "version": "1.10.0",
            }
            assert package_is_installed(prefix, "six=1.10.0")
            output, err, _ = run_command(Commands.RUN, prefix, "python", "-m", "pip", "freeze")
            pkgs = set(ensure_text_type(v.strip()) for v in output.splitlines() if v.strip())
            assert "six==1.10.0" in pkgs

            six_record = next(PrefixData(prefix).query("six"))
            print(json_dump(six_record))
            assert json_loads(json_dump(six_record)) == {
                "build": "pypi_0",
                "build_number": 0,
                "channel": "https://conda.anaconda.org/pypi",
                "constrains": [],
                "depends": [
                    "python 3.5.*"
                ],
                "files": [
                    sp_dir + "/" + "__pycache__/six.cpython-35.pyc",
                    sp_dir + "/" + "six-1.10.0.dist-info/DESCRIPTION.rst",
                    sp_dir + "/" + "six-1.10.0.dist-info/INSTALLER",
                    sp_dir + "/" + "six-1.10.0.dist-info/METADATA",
                    sp_dir + "/" + "six-1.10.0.dist-info/RECORD",
                    sp_dir + "/" + "six-1.10.0.dist-info/WHEEL",
                    sp_dir + "/" + "six-1.10.0.dist-info/metadata.json",
                    sp_dir + "/" + "six-1.10.0.dist-info/top_level.txt",
                    sp_dir + "/" + "six.py",
                ],
                "fn": "six-1.10.0.dist-info",
                "name": "six",
                "package_type": "virtual_python_wheel",
                "paths_data": {
                    "paths": [
                        {
                            "_path": sp_dir + "/" + "__pycache__/six.cpython-35.pyc",
                            "path_type": "hardlink",
                            "sha256": None,
                            "size_in_bytes": None
                        },
                        {
                            "_path": sp_dir + "/" + "six-1.10.0.dist-info/DESCRIPTION.rst",
                            "path_type": "hardlink",
                            "sha256": "QWBtSTT2zzabwJv1NQbTfClSX13m-Qc6tqU4TRL1RLs",
                            "size_in_bytes": 774
                        },
                        {
                            "_path": sp_dir + "/" + "six-1.10.0.dist-info/INSTALLER",
                            "path_type": "hardlink",
                            "sha256": "zuuue4knoyJ-UwPPXg8fezS7VCrXJQrAP7zeNuwvFQg",
                            "size_in_bytes": 4
                        },
                        {
                            "_path": sp_dir + "/" + "six-1.10.0.dist-info/METADATA",
                            "path_type": "hardlink",
                            "sha256": "5HceJsUnHof2IRamlCKO2MwNjve1eSP4rLzVQDfwpCQ",
                            "size_in_bytes": 1283
                        },
                        {
                            "_path": sp_dir + "/" + "six-1.10.0.dist-info/RECORD",
                            "path_type": "hardlink",
                            "sha256": None,
                            "size_in_bytes": None
                        },
                        {
                            "_path": sp_dir + "/" + "six-1.10.0.dist-info/WHEEL",
                            "path_type": "hardlink",
                            "sha256": "GrqQvamwgBV4nLoJe0vhYRSWzWsx7xjlt74FT0SWYfE",
                            "size_in_bytes": 110
                        },
                        {
                            "_path": sp_dir + "/" + "six-1.10.0.dist-info/metadata.json",
                            "path_type": "hardlink",
                            "sha256": "jtOeeTBubYDChl_5Ql5ZPlKoHgg6rdqRIjOz1e5Ek2U",
                            "size_in_bytes": 658
                        },
                        {
                            "_path": sp_dir + "/" + "six-1.10.0.dist-info/top_level.txt",
                            "path_type": "hardlink",
                            "sha256": "_iVH_iYEtEXnD8nYGQYpYFUvkUW9sEO1GYbkeKSAais",
                            "size_in_bytes": 4
                        },
                        {
                            "_path": sp_dir + "/" + "six.py",
                            "path_type": "hardlink",
                            "sha256": "A6hdJZVjI3t_geebZ9BzUvwRrIXo0lfwzQlM2LcKyas",
                            "size_in_bytes": 30098
                        }
                    ],
                    "paths_version": 1
                },
                "subdir": "pypi",
                "version": "1.10.0"
            }

            stdout, stderr, _ = run_command(Commands.INSTALL, prefix, "six", "--satisfied-skip-solve")
            assert not stderr
            assert "All requested packages already installed." in stdout

            stdout, stderr, _ = run_command(Commands.INSTALL, prefix, "six", "--repodata-fn",
                                            "repodata.json")
            assert not stderr
            assert package_is_installed(prefix, "six>=1.11")
            output, err, _ = run_command(Commands.RUN, prefix, "python", "-m", "pip", "freeze")
            pkgs = set(ensure_text_type(v.strip()) for v in output.splitlines() if v.strip())
            six_record = next(PrefixData(prefix).query("six"))
            assert "six==%s" % six_record.version in pkgs

            assert len(glob(join(prefix, "conda-meta", "six-*.json"))) == 1

            output, err, _ = run_command(Commands.RUN, prefix, "python", "-m", "pip", "install", "-U", "six==1.10")
            print(output)
            assert "Successfully installed six-1.10.0" in ensure_text_type(output)
            PrefixData._cache_.clear()
            assert package_is_installed(prefix, "six=1.10.0")

            stdout, stderr, _ = run_command(Commands.REMOVE, prefix, "six")
            assert not stderr
            assert "six-1.10.0-pypi_0" in stdout
            assert not package_is_installed(prefix, "six")

            assert not glob(join(prefix, sp_dir, "six*"))


    def test_conda_pip_interop_conda_editable_package(self):
        with env_var('CONDA_RESTORE_FREE_CHANNEL', True, stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with make_temp_env("python=2.7", "pip=10", "git", use_restricted_unicode=on_win) as prefix:
                workdir = prefix

                run_command(Commands.CONFIG, prefix, "--set", "pip_interop_enabled", "true")
                assert package_is_installed(prefix, "python")

                # install an "editable" urllib3 that cannot be managed
                output, err, _ = run_command(Commands.RUN, prefix, '--cwd', workdir,
                                             "python", "-m", "pip", "install", "-e",
                                             "git+https://github.com/urllib3/urllib3.git@1.19.1#egg=urllib3")
                assert isfile(join(workdir, "src", "urllib3", "urllib3", "__init__.py"))
                assert not isfile(join("src", "urllib3", "urllib3", "__init__.py"))
                PrefixData._cache_.clear()
                assert package_is_installed(prefix, "urllib3")
                urllib3_record = next(PrefixData(prefix).query("urllib3"))
                urllib3_record_dump = urllib3_record.dump()
                files = urllib3_record_dump.pop("files")
                paths_data = urllib3_record_dump.pop("paths_data")
                print(json_dump(urllib3_record_dump))

                assert json_loads(json_dump(urllib3_record_dump)) == {
                    "build": "dev_0",
                    "build_number": 0,
                    "channel": "https://conda.anaconda.org/<develop>",
                    "constrains": [
                        "cryptography >=1.3.4",
                        "idna >=2.0.0",
                        "pyopenssl >=0.14",
                        "pysocks !=1.5.7,<2.0,>=1.5.6"
                    ],
                    "depends": [
                        "python 2.7.*"
                    ],
                    "fn": "urllib3-1.19.1-dev_0",
                    "name": "urllib3",
                    "package_type": "virtual_python_egg_link",
                    "subdir": "pypi",
                    "version": "1.19.1"
                }

                # the unmanageable urllib3 should prevent a new requests from being installed
                stdout, stderr, _ = run_command(Commands.INSTALL, prefix,
                                                "requests", "--dry-run", "--json",
                                                use_exception_handler=True)
                assert not stderr
                json_obj = json_loads(stdout)
                assert "UNLINK" not in json_obj["actions"]
                link_dists = json_obj["actions"]["LINK"]
                assert len(link_dists) == 1
                assert link_dists[0]["name"] == "requests"
                assert VersionOrder(link_dists[0]["version"]) < VersionOrder("2.16")

                # should already be satisfied
                stdout, stderr, _ = run_command(Commands.INSTALL, prefix, "urllib3", "-S")
                assert "All requested packages already installed." in stdout

                # should raise an error
                with pytest.raises(PackagesNotFoundError):
                    # TODO: This raises PackagesNotFoundError, but the error should really explain
                    #       that we can't install urllib3 because it's already installed and
                    #       unmanageable. The error should suggest trying to use pip to uninstall it.
                    stdout, stderr, _ = run_command(Commands.INSTALL, prefix, "urllib3=1.20", "--dry-run")

                # Now install a manageable urllib3.
                output = check_output(PYTHON_BINARY + " -m pip install -U urllib3==1.20",
                                    cwd=prefix, shell=True)
                print(output)
                PrefixData._cache_.clear()
                assert package_is_installed(prefix, "urllib3")
                urllib3_record = next(PrefixData(prefix).query("urllib3"))
                urllib3_record_dump = urllib3_record.dump()
                files = urllib3_record_dump.pop("files")
                paths_data = urllib3_record_dump.pop("paths_data")
                print(json_dump(urllib3_record_dump))

                assert json_loads(json_dump(urllib3_record_dump)) == {
                    "build": "pypi_0",
                    "build_number": 0,
                    "channel": "https://conda.anaconda.org/pypi",
                    "constrains": [
                        "pysocks >=1.5.6,<2.0,!=1.5.7"
                    ],
                    "depends": [
                        "python 2.7.*"
                    ],
                    "fn": "urllib3-1.20.dist-info",
                    "name": "urllib3",
                    "package_type": "virtual_python_wheel",
                    "subdir": "pypi",
                    "version": "1.20"
                }

                # we should be able to install an unbundled requests that upgrades urllib3 in the process
                stdout, stderr, _ = run_command(Commands.INSTALL, prefix, "requests=2.18", "--json")
                assert package_is_installed(prefix, "requests")
                assert package_is_installed(prefix, "urllib3>=1.21")
                assert not stderr
                json_obj = json_loads(stdout)
                unlink_dists = [
                    dist_obj for dist_obj in json_obj["actions"]["UNLINK"] if dist_obj.get("platform") == "pypi"
                ]  # filter out conda package upgrades like python and libffi
                assert len(unlink_dists) == 1
                assert unlink_dists[0]["name"] == "urllib3"
                assert unlink_dists[0]["channel"] == "pypi"


    def test_conda_pip_interop_compatible_release_operator(self):
        # Regression test for #7776
        # important to start the env with six 1.9.  That version forces an upgrade later in the test
        with make_temp_env("-c", "https://repo.anaconda.com/pkgs/free", "pip=10", "six=1.9", "appdirs",
                           use_restricted_unicode=on_win) as prefix:
            run_command(Commands.CONFIG, prefix, "--set", "pip_interop_enabled", "true")
            assert package_is_installed(prefix, "python")
            assert package_is_installed(prefix, "six=1.9")
            assert package_is_installed(prefix, "appdirs>=1.4.3")

            python_binary = join(prefix, PYTHON_BINARY)
            p = Popen([python_binary, '-m', 'pip', 'install', 'fs==2.1.0'],
                      stdout=PIPE, stderr=PIPE, cwd=prefix, shell=False)
            stdout, stderr = p.communicate()
            rc = p.returncode
            assert int(rc) != 0
            stderr = stderr.decode('utf-8', errors='replace') if hasattr(stderr, 'decode') else text_type(stderr)
            assert "Cannot uninstall" in stderr

            run_command(Commands.REMOVE, prefix, "six")
            assert not package_is_installed(prefix, "six")

            output = check_output([python_binary, '-m', 'pip', 'install', 'fs==2.1.0'], cwd=prefix, shell=False)
            print(output)
            PrefixData._cache_.clear()
            assert package_is_installed(prefix, "fs==2.1.0")
            # six_record = next(PrefixData(prefix).query("six"))
            # print(json_dump(six_record.dump()))
            assert package_is_installed(prefix, "six~=1.10")

            stdout, stderr, _ = run_command(Commands.LIST, prefix)
            assert not stderr
            assert "fs                        2.1.0                    pypi_0    pypi" in stdout

            with pytest.raises(DryRunExit):
                run_command(Commands.INSTALL, prefix, "-c", "https://repo.anaconda.com/pkgs/free",
                            "agate=1.6", "--dry-run")

    @pytest.mark.skipif(sys.version_info.major == 2 and context.subdir == "win-32", reason="Incompatible DLLs with win-32 python 2.7 ")
    def test_conda_recovery_of_pip_inconsistent_env(self):
        with make_temp_env("pip=10", "python", "anaconda-client",
                           use_restricted_unicode=on_win) as prefix:
            run_command(Commands.CONFIG, prefix, "--set", "pip_interop_enabled", "true")
            assert package_is_installed(prefix, "python")
            assert package_is_installed(prefix, "anaconda-client>=1.7.2")

            stdout, stderr, _ = run_command(Commands.REMOVE, prefix, 'requests', '--force')
            assert not stderr

            # this is incompatible with anaconda-client
            python_binary = join(prefix, PYTHON_BINARY)
            p = Popen([python_binary, '-m', 'pip', 'install', 'requests==2.8'],
                      stdout=PIPE, stderr=PIPE, cwd=prefix, shell=False)
            stdout, stderr = p.communicate()
            rc = p.returncode
            assert int(rc) == 0

            stdout, stderr, _ = run_command(Commands.INSTALL, prefix, 'imagesize', '--json')
            assert json.loads(stdout)['success']
            assert "The environment is inconsistent" in stderr

            stdout, stderr, _ = run_command(Commands.LIST, prefix, '--json')
            pkgs = json.loads(stdout)
            for entry in pkgs:
                if entry['name'] == "requests":
                    assert VersionOrder(entry['version']) >= VersionOrder("2.9.1")

    def test_install_freezes_env_by_default(self):
        """We pass --no-update-deps/--freeze-installed by default, effectively.  This helps speed things
        up by not considering changes to existing stuff unless the solve ends up unsatisfiable."""

        # create an initial env
        with make_temp_env("python=2", use_restricted_unicode=on_win, no_capture=True) as prefix:
            assert package_is_installed(prefix, "python=2.7.*")
            # Install a version older than the last one
            run_command(Commands.INSTALL, prefix, "setuptools=40.*")

            stdout, stderr, _ = run_command(Commands.LIST, prefix, '--json')

            pkgs = json.loads(stdout)

            run_command(Commands.INSTALL, prefix, "imagesize", "--freeze-installed")

            stdout, _, _ = run_command(Commands.LIST, prefix, '--json')
            pkgs_after_install = json.loads(stdout)

            # Compare before and after installing package
            for pkg in pkgs:
                for pkg_after in pkgs_after_install:
                    if pkg["name"] == pkg_after["name"]:
                        assert pkg["version"] == pkg_after["version"]

    @pytest.mark.skipif(on_win, reason="gawk is a windows only package")
    def test_search_gawk_not_win_filter(self):
        with make_temp_env() as prefix:
            stdout, stderr, _ = run_command(
                Commands.SEARCH, prefix, "*gawk", "--platform", "win-64", "--json",
                "-c", "https://repo.anaconda.com/pkgs/msys2", "--json",
                use_exception_handler=True,
            )
            json_obj = json_loads(stdout.replace("Fetching package metadata ...", "").strip())
            assert "m2-gawk" in json_obj.keys()
            assert len(json_obj.keys()) == 1

    @pytest.mark.skipif(not on_win, reason="gawk is a windows only package")
    def test_search_gawk_on_win(self):
        with make_temp_env() as prefix:
            stdout, _, _ = run_command(Commands.SEARCH, prefix, "*gawk", "--json", use_exception_handler=True)
            json_obj = json_loads(stdout.replace("Fetching package metadata ...", "").strip())
            assert "m2-gawk" in json_obj.keys()
            assert len(json_obj.keys()) == 1

    @pytest.mark.skipif(not on_win, reason="gawk is a windows only package")
    def test_search_gawk_on_win_filter(self):
        with make_temp_env() as prefix:
            stdout, _, _ = run_command(Commands.SEARCH, prefix, "gawk", "--platform",
                                    "linux-64", "--json", use_exception_handler=True)
            json_obj = json_loads(stdout.replace("Fetching package metadata ...", "").strip())
            assert not len(json_obj.keys()) == 0

    def test_bad_anaconda_token_infinite_loop(self):
        # This test is being changed around 2017-10-17, when the behavior of anaconda.org
        # was changed.  Previously, an expired token would return with a 401 response.
        # Now, a 200 response is always given, with any public packages available on the channel.
        response = requests.get("https://conda.anaconda.org/t/cqgccfm1mfma/data-portal/"
                                "%s/repodata.json" % context.subdir)
        assert response.status_code == 200

        try:
            prefix = make_temp_prefix(str(uuid4())[:7])
            channel_url = "https://conda.anaconda.org/t/cqgccfm1mfma/data-portal"
            run_command(Commands.CONFIG, prefix, "--add", "channels", channel_url)
            stdout, stderr, _ = run_command(Commands.CONFIG, prefix, "--show")
            yml_obj = yaml_round_trip_load(stdout)
            assert yml_obj['channels'] == [channel_url.replace('cqgccfm1mfma', '<TOKEN>'), 'defaults']

            with pytest.raises(PackagesNotFoundError):
                run_command(Commands.SEARCH, prefix, "boltons", "--json")

            stdout, stderr, _ = run_command(Commands.SEARCH, prefix, "anaconda-mosaic", "--json")

            json_obj = json.loads(stdout)
            assert "anaconda-mosaic" in json_obj
            assert len(json_obj["anaconda-mosaic"]) > 0

        finally:
            rmtree(prefix, ignore_errors=True)
            reset_context()

    def test_anaconda_token_with_private_package(self):
        # TODO: should also write a test to use binstar_client to set the token,
        # then let conda load the token

        # Step 0. xfail if a token is set, for example when testing locally
        tokens = read_binstar_tokens()
        if tokens:
            pytest.xfail("binstar token found in global configuration")

        # Step 1. Make sure without the token we don't see the anyjson package
        try:
            prefix = make_temp_prefix(str(uuid4())[:7])
            channel_url = "https://conda.anaconda.org/kalefranz"
            run_command(Commands.CONFIG, prefix, "--add", "channels", channel_url)
            run_command(Commands.CONFIG, prefix, "--remove", "channels", "defaults")
            output, _, _ = run_command(Commands.CONFIG, prefix, "--show")
            yml_obj = yaml_round_trip_load(output)
            assert yml_obj['channels'] == [channel_url]

            output, _, _ = run_command(Commands.SEARCH, prefix, "anyjson", "--platform",
                                         "linux-64", "--json", use_exception_handler=True)
            json_obj = json_loads(output)
            assert json_obj['exception_name'] == 'PackagesNotFoundError'

        finally:
            rmtree(prefix, ignore_errors=True)
            reset_context()

        # Step 2. Now with the token make sure we can see the anyjson package
        try:
            prefix = make_temp_prefix(str(uuid4())[:7])
            channel_url = "https://conda.anaconda.org/t/zlZvSlMGN7CB/kalefranz"
            run_command(Commands.CONFIG, prefix, "--add", "channels", channel_url)
            run_command(Commands.CONFIG, prefix, "--remove", "channels", "defaults")
            stdout, stderr, _ = run_command(Commands.CONFIG, prefix, "--show")
            yml_obj = yaml_round_trip_load(stdout)

            assert yml_obj['channels'] == ["https://conda.anaconda.org/t/<TOKEN>/kalefranz"]

            stdout, stderr, _ = run_command(Commands.SEARCH, prefix, "anyjson", "--platform",
                                         "linux-64", "--json")
            json_obj = json_loads(stdout)
            assert 'anyjson' in json_obj

        finally:
            rmtree(prefix, ignore_errors=True)

    def test_clean_index_cache(self):
        prefix = ''

        # make sure we have something in the index cache
        stdout, stderr, _ = run_command(Commands.INFO, prefix, "bzip2", "--json")
        assert "bzip2" in json_loads(stdout)
        index_cache_dir = create_cache_dir()
        assert glob(join(index_cache_dir, "*.json"))

        # now clear it
        run_command(Commands.CLEAN, prefix, "--index-cache")
        assert not glob(join(index_cache_dir, "*.json"))

    def test_use_index_cache(self):
        from conda.gateways.connection.session import CondaSession
        from conda.core.subdir_data import SubdirData
        SubdirData._cache_.clear()

        prefix = make_temp_prefix("_" + str(uuid4())[:7])
        with make_temp_env(prefix=prefix, no_capture=True):
            # First, clear the index cache to make sure we start with an empty cache.
            index_cache_dir = create_cache_dir()
            run_command(Commands.CLEAN, '', "--index-cache")
            assert not glob(join(index_cache_dir, "*.json"))

            # Then, populate the index cache.
            orig_get = CondaSession.get
            with patch.object(CondaSession, 'get', autospec=True) as mock_method:
                def side_effect(self, url, **kwargs):
                    # Make sure that we don't use the cache because of the
                    # corresponding HTTP header. This test is supposed to test
                    # whether the --use-index-cache causes the cache to be used.
                    result = orig_get(self, url, **kwargs)
                    for header in ['Etag', 'Last-Modified', 'Cache-Control']:
                        if header in result.headers:
                            del result.headers[header]
                    return result

                SubdirData._cache_.clear()
                mock_method.side_effect = side_effect
                stdout, stderr, _ = run_command(Commands.INFO, prefix, "flask", "--json")
                assert mock_method.called

            # Next run with --use-index-cache and make sure it actually hits the cache
            # and does not go out fetching index data remotely.
            with patch.object(CondaSession, 'get', autospec=True) as mock_method:
                def side_effect(self, url, **kwargs):
                    if url.endswith('/repodata.json') or url.endswith('/repodata.json.bz2'):
                        raise AssertionError('Index cache was not hit')
                    else:
                        return orig_get(self, url, **kwargs)

                mock_method.side_effect = side_effect
                run_command(Commands.INSTALL, prefix, "flask", "--json", "--use-index-cache")

    def test_offline_with_empty_index_cache(self):
        from conda.core.subdir_data import SubdirData
        SubdirData._cache_.clear()

        try:
            with make_temp_env(use_restricted_unicode=on_win) as prefix:
                pkgs_dir = join(prefix, 'pkgs')
                with env_var('CONDA_PKGS_DIRS', pkgs_dir, stack_callback=conda_tests_ctxt_mgmt_def_pol):
                    with make_temp_channel(['flask-0.12.2']) as channel:
                        # Clear the index cache.
                        index_cache_dir = create_cache_dir()
                        run_command(Commands.CLEAN, '', "--index-cache")
                        assert not exists(index_cache_dir)

                        # Then attempt to install a package with --offline. The package (flask) is
                        # available in a local channel, however its dependencies are not. Make sure
                        # that a) it fails because the dependencies are not available and b)
                        # we don't try to download the repodata from non-local channels but we do
                        # download repodata from local channels.
                        from conda.gateways.connection.session import CondaSession

                        orig_get = CondaSession.get

                        result_dict = {}
                        def side_effect(self, url, **kwargs):
                            if not url.startswith('file://'):
                                raise AssertionError('Attempt to fetch repodata: {}'.format(url))
                            if url.startswith(channel):
                                result_dict['local_channel_seen'] = True
                            return orig_get(self, url, **kwargs)

                        with patch.object(CondaSession, 'get', autospec=True) as mock_method:
                            mock_method.side_effect = side_effect

                            SubdirData._cache_.clear()

                            # This first install passes because flask and its dependencies are in the
                            # package cache.
                            assert not package_is_installed(prefix, "flask")
                            run_command(Commands.INSTALL, prefix, "-c", channel, "flask", "--offline")
                            assert package_is_installed(prefix, "flask")

                            # The mock should have been called with our local channel URL though.
                            assert result_dict.get('local_channel_seen')

                            # Fails because pytz cannot be found in available channels.
                            with pytest.raises(PackagesNotFoundError):
                                run_command(Commands.INSTALL, prefix, "-c", channel, "pytz", "--offline")
                            assert not package_is_installed(prefix, "pytz")
        finally:
            SubdirData._cache_.clear()

    def test_create_from_extracted(self):
        with make_temp_package_cache() as pkgs_dir:
            assert context.pkgs_dirs == (pkgs_dir,)
            def pkgs_dir_has_tarball(tarball_prefix):
                return any(f.startswith(tarball_prefix) and any(f.endswith(ext) for ext in CONDA_PACKAGE_EXTENSIONS)
                           for f in os.listdir(pkgs_dir))

            with make_temp_env() as prefix:
                # First, make sure the openssl package is present in the cache,
                # downloading it if needed
                assert not pkgs_dir_has_tarball('openssl-')
                run_command(Commands.INSTALL, prefix, 'openssl')
                assert pkgs_dir_has_tarball('openssl-')

                # Then, remove the tarball but keep the extracted directory around
                run_command(Commands.CLEAN, prefix, '--tarballs', '--yes')
                assert not pkgs_dir_has_tarball('openssl-')

            with make_temp_env() as prefix:
                # Finally, install openssl, enforcing the use of the extracted package.
                # We expect that the tarball does not appear again because we simply
                # linked the package from the extracted directory. If the tarball
                # appeared again, we decided to re-download the package for some reason.
                run_command(Commands.INSTALL, prefix, 'openssl', '--offline')
                assert not pkgs_dir_has_tarball('openssl-')

    def test_clean_tarballs_and_packages(self):
        with make_temp_package_cache() as pkgs_dir:
            filter_pkgs = lambda x: [f for f in x if (f.endswith('.tar.bz2') or f.endswith('.conda'))]
            with make_temp_env("bzip2") as prefix:
                pkgs_dir_contents = [join(pkgs_dir, d) for d in os.listdir(pkgs_dir)]
                pkgs_dir_dirs = [d for d in pkgs_dir_contents if isdir(d)]
                pkgs_dir_tarballs = filter_pkgs(pkgs_dir_contents)
                assert any(basename(d).startswith('bzip2-') for d in pkgs_dir_dirs)
                assert any(basename(f).startswith('bzip2-') for f in pkgs_dir_tarballs)

                # --json flag is regression test for #5451
                run_command(Commands.CLEAN, prefix, "--packages", "--yes", "--json")

                # --json flag is regression test for #5451
                run_command(Commands.CLEAN, prefix, "--tarballs", "--yes", "--json")

                pkgs_dir_contents = [join(pkgs_dir, d) for d in os.listdir(pkgs_dir)]
                pkgs_dir_dirs = [d for d in pkgs_dir_contents if isdir(d)]
                pkgs_dir_tarballs = filter_pkgs(pkgs_dir_contents)

                assert any(basename(d).startswith('bzip2-') for d in pkgs_dir_dirs)
                assert not any(basename(f).startswith('bzip2-') for f in pkgs_dir_tarballs)

                run_command(Commands.REMOVE, prefix, "bzip2", "--yes", "--json")

            run_command(Commands.CLEAN, prefix, "--packages", "--yes")

            pkgs_dir_contents = [join(pkgs_dir, d) for d in os.listdir(pkgs_dir)]
            pkgs_dir_dirs = [d for d in pkgs_dir_contents if isdir(d)]
            assert not any(basename(d).startswith('bzip2-') for d in pkgs_dir_dirs)

    def test_install_mkdir(self):
        try:
            prefix = make_temp_prefix()
            with open(os.path.join(prefix, 'tempfile.txt'), "w") as f:
                f.write('test')
            assert isdir(prefix)
            assert isfile(os.path.join(prefix, 'tempfile.txt'))
            with pytest.raises(DirectoryNotACondaEnvironmentError):
                run_command(Commands.INSTALL, prefix, "python=3.7.2", "--mkdir")

            run_command(Commands.CREATE, prefix)
            run_command(Commands.INSTALL, prefix, "python=3.7.2", "--mkdir")
            assert package_is_installed(prefix, "python=3.7.2")

            rm_rf(prefix, clean_empty_parents=True)
            assert path_is_clean(prefix)

            # this part also a regression test for #4849
            run_command(Commands.INSTALL, prefix, "python-dateutil=2.6.1", "python=3.5.6", "--mkdir", no_capture=True)
            assert package_is_installed(prefix, "python=3.5.6")
            assert package_is_installed(prefix, "python-dateutil=2.6.1")

        finally:
            rm_rf(prefix, clean_empty_parents=True)

    @pytest.mark.skipif(on_win, reason="python doesn't have dependencies on windows")
    def test_disallowed_packages(self):
        with make_temp_env() as prefix:
            with env_var('CONDA_DISALLOWED_PACKAGES', 'sqlite&flask', stack_callback=conda_tests_ctxt_mgmt_def_pol):
                with pytest.raises(CondaMultiError) as exc:
                    run_command(Commands.INSTALL, prefix, 'python')
            exc_val = exc.value.errors[0]
            assert isinstance(exc_val, DisallowedPackageError)
            assert exc_val.dump_map()['package_ref']['name'] == 'sqlite'

    def test_dont_remove_conda_1(self):
        pkgs_dirs = context.pkgs_dirs
        prefix = make_temp_prefix()
        with env_vars({
            'CONDA_ROOT_PREFIX': prefix,
            'CONDA_PKGS_DIRS': ','.join(pkgs_dirs)
        }, stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with make_temp_env(prefix=prefix):
                _, _, _ = run_command(Commands.INSTALL, prefix, "conda", "conda-build")
                assert package_is_installed(prefix, "conda")
                assert package_is_installed(prefix, "pycosat")
                assert package_is_installed(prefix, "conda-build")

                with pytest.raises(CondaMultiError) as exc:
                    run_command(Commands.REMOVE, prefix, 'conda')

                assert any(isinstance(e, RemoveError) for e in exc.value.errors)
                assert package_is_installed(prefix, "conda")
                assert package_is_installed(prefix, "pycosat")

                with pytest.raises(CondaMultiError) as exc:
                    run_command(Commands.REMOVE, prefix, 'pycosat')

                assert any(isinstance(e, RemoveError) for e in exc.value.errors)
                assert package_is_installed(prefix, "conda")
                assert package_is_installed(prefix, "pycosat")
                assert package_is_installed(prefix, "conda-build")

    def test_dont_remove_conda_2(self):
        # regression test for #6904
        pkgs_dirs = context.pkgs_dirs
        prefix = make_temp_prefix()
        with make_temp_env(prefix=prefix):
            with env_vars({
                'CONDA_ROOT_PREFIX': prefix,
                'CONDA_PKGS_DIRS': ','.join(pkgs_dirs)
            }, stack_callback=conda_tests_ctxt_mgmt_def_pol):
                _, _, _ = run_command(Commands.INSTALL, prefix, "conda")
                assert package_is_installed(prefix, "conda")
                assert package_is_installed(prefix, "pycosat")

                with pytest.raises(CondaMultiError) as exc:
                    run_command(Commands.REMOVE, prefix, 'pycosat')

                assert any(isinstance(e, RemoveError) for e in exc.value.errors)
                assert package_is_installed(prefix, "conda")
                assert package_is_installed(prefix, "pycosat")

                with pytest.raises(CondaMultiError) as exc:
                    run_command(Commands.REMOVE, prefix, 'conda')

                assert any(isinstance(e, RemoveError) for e in exc.value.errors)
                assert package_is_installed(prefix, "conda")
                assert package_is_installed(prefix, "pycosat")

    def test_force_remove(self):
        with make_temp_env() as prefix:
            stdout, stderr, _ = run_command(Commands.INSTALL, prefix, "libarchive")
            assert package_is_installed(prefix, "libarchive")
            assert package_is_installed(prefix, "xz")

            stdout, stderr, _ = run_command(Commands.REMOVE, prefix, "xz", "--force")
            assert not package_is_installed(prefix, "xz")
            assert package_is_installed(prefix, "libarchive")

            stdout, stderr, _ = run_command(Commands.REMOVE, prefix, "libarchive")
            assert not package_is_installed(prefix, "libarchive")

        # regression test for #3489
        # don't raise for remove --all if environment doesn't exist
        rm_rf(prefix, clean_empty_parents=True)
        run_command(Commands.REMOVE, prefix, "--all")

    def test_download_only_flag(self):
        from conda.core.link import UnlinkLinkTransaction
        with patch.object(UnlinkLinkTransaction, 'execute') as mock_method:
            with make_temp_env('openssl', '--download-only', use_exception_handler=True) as prefix:
                assert mock_method.call_count == 0
            with make_temp_env('openssl', use_exception_handler=True) as prefix:
                assert mock_method.call_count == 1

    def test_transactional_rollback_simple(self):
        from conda.core.path_actions import CreatePrefixRecordAction
        with patch.object(CreatePrefixRecordAction, 'execute') as mock_method:
            with make_temp_env() as prefix:
                mock_method.side_effect = KeyError('Bang bang!!')
                with pytest.raises(CondaMultiError):
                    run_command(Commands.INSTALL, prefix, 'openssl')
                assert not package_is_installed(prefix, 'openssl')

    def test_transactional_rollback_upgrade_downgrade(self):
        with make_temp_env("python=3.5", no_capture=True) as prefix:
            assert exists(join(prefix, PYTHON_BINARY))
            assert package_is_installed(prefix, 'python=3')

            run_command(Commands.INSTALL, prefix, 'flask=0.12.2')
            assert package_is_installed(prefix, 'flask=0.12.2')

            from conda.core.path_actions import CreatePrefixRecordAction
            with patch.object(CreatePrefixRecordAction, 'execute') as mock_method:
                mock_method.side_effect = KeyError('Bang bang!!')
                with pytest.raises(CondaMultiError):
                    run_command(Commands.INSTALL, prefix, 'flask=1.0.2')
                assert package_is_installed(prefix, 'flask=0.12.2')

    def test_directory_not_a_conda_environment(self):
        prefix = make_temp_prefix(str(uuid4())[:7])
        with open(join(prefix, 'tempfile.txt'), 'w') as f:
            f.write("weeee")
        try:
            with pytest.raises(DirectoryNotACondaEnvironmentError):
                run_command(Commands.INSTALL, prefix, "sqlite")
        finally:
            rm_rf(prefix)

    def test_multiline_run_command(self):
        with make_temp_env() as prefix:
            env_which_etc, errs_etc, _ = run_command(Commands.RUN, prefix, '--cwd', prefix, dedent("""
            {env} | sort
            {which} conda
            """.format(env=env_or_set, which=which_or_where)), dev=True)
        assert env_which_etc
        assert not errs_etc

    @pytest.mark.xfail(on_mac, reason="see #11128")
    def test_init_dev_and_NoBaseEnvironmentError(self):
        # This specific python version is named so that the test suite uses an
        # old python build that still hacks 'Library/bin' into PATH. Really, we
        # should run all of these conda commands through run_command(RUN) which
        # would wrap them with activation.

        # We pass --copy because otherwise the call to conda init --dev will overwrite
        # the following files in the package cache:
        # Library/bin/conda.bat
        # Scripts/activate.bat
        # Scripts/conda-env-script.py
        # Scripts/conda-script.py
        # .. and from then onwards, that conda package is corrupt in the cache.
        # Note: We were overwriting some *old* conda package with files from this latest
        #       source code. Urgh.

        conda_v = "4.5.13"
        python_v = "3.6.7"
        # conda-package-handling is necessary here because we install a dev version of conda
        with make_temp_env("conda="+conda_v, "python="+python_v, "git",
                           "conda-package-handling", "--copy",
                           name='_' + str(uuid4())[:8]) as prefix:
            # We cannot naively call $SOME_PREFIX/bin/conda and expect it to run the right conda because we
            # respect PATH (i.e. our conda shell script (in 4.5 days at least) has the following shebang:
            # `#!/usr/bin/env python`). Now it may be that `PYTHONPATH` or something was meant to account
            # for this and my clean_env stuff gets in the way but let's just be explicit about the Python
            # instead.  If we ran any conda stuff that needs ssl on Windows then we'd need to use
            # Commands.RUN here, but on Unix we'll be fine.
            conda_exe = join(prefix, 'Scripts', 'conda.exe') if on_win else join(prefix, 'bin', 'conda')
            with env_var('CONDA_BAT' if on_win else 'CONDA_EXE', conda_exe, stack_callback=conda_tests_ctxt_mgmt_def_pol):
                result = subprocess_call_with_clean_env([conda_exe, "--version"], path=prefix)
                assert result.rc == 0
                # Python returns --version in stderr. This used to `assert not result.stderr` and I am
                # not entirely sure why that didn't cause problems before. Unfortunately pycharm outputs
                # 'pydev debugger: process XXXX is connecting" to stderr sometimes.  Need to see why we
                # are crossing our streams.
                # assert not (result.stderr and result.stdout), "--version should output to one stream only"
                version = result.stdout if result.stdout else result.stderr
                assert version.startswith("conda ")
                conda_version = version.strip()[6:]
                assert conda_version == conda_v

                # When we run `conda run -p prefix python -m conda init` we are explicitly wishing to run the
                # old Python 3.6.7 in prefix, but against the development sources of conda. Those are found
                # via `workdir=CONDA_SOURCE_ROOT`.
                #
                # This was beyond complicated to deal with and led to adding a new 'dev' flag which modifies
                # what the script wrappers emit for `CONDA_EXE`.
                #
                # Normal mode: CONDA_EXE=[join(prefix,'bin','conda')]
                #    Dev mode: CONDA_EXE=[join(root.prefix+'bin'+'python'), '-m', 'conda']
                #
                # When you next need to debug this stuff (and you will), the following may help you:
                #

                '''
                env_path_etc, errs_etc, _ = run_command(Commands.RUN, prefix, '--cwd', CONDA_SOURCE_ROOT, dedent("""
                    declare -f
                    env | sort
                    which conda
                    cat $(which conda)
                    echo $PATH
                    conda info
                    """), dev=True)
                log.warning(env_path_etc)
                log.warning(errs_etc)
                '''

                # Let us test that the conda we expect to be running in that scenario
                # is the conda that actually runs:
                conda__file__, stderr, _ = run_command(
                    Commands.RUN,
                    prefix,
                    "--cwd",
                    CONDA_SOURCE_ROOT,
                    sys.executable,
                    "-c",
                    "import conda, os, sys; " "sys.stdout.write(os.path.abspath(conda.__file__))",
                    dev=True,
                )
                assert dirname(dirname(conda__file__)) == CONDA_SOURCE_ROOT

                # (and the same thing for Python)
                python_v2, _, _ = run_command(
                    Commands.RUN,
                    prefix,
                    "--cwd",
                    CONDA_SOURCE_ROOT,
                    "python",
                    "-c",
                    "import os, sys; "
                    "sys.stdout.write(str(sys.version_info[0]) + '.' + "
                    "                 str(sys.version_info[1]) + '.' + "
                    "                 str(sys.version_info[2]))", dev=True)
                assert python_v2 == python_v

                # install a dev version with our current source checkout into prefix
                args = ["python", "-m", "conda", "init", *(["cmd.exe"] if on_win else []), "--dev"]
                result, stderr, _ = run_command(
                    Commands.RUN,
                    prefix,
                    "--cwd",
                    CONDA_SOURCE_ROOT,
                    *args,
                    dev=True,
                )

                result = subprocess_call_with_clean_env("%s --version" % conda_exe)
                assert result.rc == 0
                assert not result.stderr
                assert result.stdout.startswith("conda ")
                conda_version = result.stdout.strip()[6:]
                assert conda_version == CONDA_VERSION

                rm_rf(join(prefix, 'conda-meta', 'history'))

                result = subprocess_call_with_clean_env("%s info -a" % conda_exe)
                print(result.stdout)

                if not on_win:
                    # Windows has: Fatal Python error: failed to get random numbers to initialize Python
                    result = subprocess_call("%s install python" % conda_exe, env={"SHLVL": "1"},
                                             raise_on_error=False)
                    assert result.rc == 1
                    assert "NoBaseEnvironmentError: This conda installation has no default base environment." in result.stderr

    # This test *was* very flaky on Python 2 when using `py_ver = sys.version_info[0]`. Changing it to `py_ver = '3'`
    # seems to work. I've done as much as I can to isolate this test.  It is a particularly tricky one.
    @pytest.mark.skip('Test is flaky')
    def test_conda_downgrade(self):
        # Create an environment with the current conda under test, but include an earlier
        # version of conda and other packages in that environment.
        # Make sure we can flip back and forth.
        with env_vars({
            "CONDA_AUTO_UPDATE_CONDA": "false",
            "CONDA_ALLOW_CONDA_DOWNGRADES": "true",
            "CONDA_DLL_SEARCH_MODIFICATION_ENABLE": "1",
        }, stack_callback=conda_tests_ctxt_mgmt_def_pol):
            # py_ver = str(sys.version_info[0])
            py_ver = "3"
            with make_temp_env("conda=4.6.14", "python=" + py_ver, "conda-package-handling", use_restricted_unicode=True,
                               name = '_' + str(uuid4())[:8]) as prefix:  # rev 0
                # See comment in test_init_dev_and_NoBaseEnvironmentError.
                python_exe = join(prefix, 'python.exe') if on_win else join(prefix, 'bin', 'python')
                conda_exe = join(prefix, 'Scripts', 'conda.exe') if on_win else join(prefix, 'bin', 'conda')
                # this is used to run the python interpreter in the env and loads our dev
                #     version of conda
                py_co = [python_exe, "-m", "conda"]
                assert package_is_installed(prefix, "conda=4.6.14")

                # runs our current version of conda to install into the foreign env
                run_command(Commands.INSTALL, prefix, "lockfile")  # rev 1
                assert package_is_installed(prefix, "lockfile")

                # runs the conda in the env to install something new into the env
                subprocess_call_with_clean_env([conda_exe, "install", "-yp", prefix, "itsdangerous"], path=prefix)  #rev 2
                PrefixData._cache_.clear()
                assert package_is_installed(prefix, "itsdangerous")

                # downgrade the version of conda in the env, using our dev version of conda
                subprocess_call(py_co + ["install", "-yp", prefix, "conda<4.6.14"], path=prefix)  #rev 3
                PrefixData._cache_.clear()
                assert not package_is_installed(prefix, "conda=4.6.14")

                # look at the revision history (for your reference, doesn't affect the test)
                stdout, stderr, _ = run_command(Commands.LIST, prefix, "--revisions")
                print(stdout)

                # undo the conda downgrade in the env (using our current outer conda version)
                PrefixData._cache_.clear()
                run_command(Commands.INSTALL, prefix, "--rev", "2")
                PrefixData._cache_.clear()
                assert package_is_installed(prefix, "conda=4.6.14")

                # use the conda in the env to revert to a previous state
                subprocess_call_with_clean_env([conda_exe, "install", "-yp", prefix, "--rev", "1"], path=prefix)
                PrefixData._cache_.clear()
                assert not package_is_installed(prefix, "itsdangerous")
                PrefixData._cache_.clear()
                assert package_is_installed(prefix, "conda=4.6.14")
                assert package_is_installed(prefix, "python=" + py_ver)

                result = subprocess_call_with_clean_env([conda_exe, "info", "--json"], path=prefix)
                conda_info = json.loads(result.stdout)
                assert conda_info["conda_version"] == "4.6.14"

    @pytest.mark.skipif(on_win, reason="openssl only has a postlink script on unix")
    def test_run_script_called(self):
        import conda.core.link
        with patch.object(conda.core.link, 'subprocess_call') as rs:
            rs.return_value = Response(None, None, 0)
            with make_temp_env("-c", "http://repo.anaconda.com/pkgs/free", "openssl=1.0.2j", "--no-deps") as prefix:
                assert package_is_installed(prefix, 'openssl')
                assert rs.call_count == 1

    @pytest.mark.xfail(on_mac, reason="known broken; see #11127")
    def test_post_link_run_in_env(self):
        test_pkg = '_conda_test_env_activated_when_post_link_executed'
        # a non-unicode name must be provided here as activate.d scripts
        # are not executed on windows, see https://github.com/conda/conda/issues/8241
        with make_temp_env(test_pkg, '-c', 'conda-test') as prefix:
            assert package_is_installed(prefix, test_pkg)

    def test_conda_info_python(self):
        output, _, _ = run_command(Commands.INFO, None, "python=3.5")
        assert "python 3.5.4" in output

    def test_toolz_cytoolz_package_cache_regression(self):
        with make_temp_env("python=3.5", use_restricted_unicode=on_win) as prefix:
            pkgs_dir = join(prefix, 'pkgs')
            with env_var('CONDA_PKGS_DIRS', pkgs_dir, stack_callback=conda_tests_ctxt_mgmt_def_pol):
                assert context.pkgs_dirs == (pkgs_dir,)
                run_command(Commands.INSTALL, prefix, "-c", "conda-forge", "toolz", "cytoolz")
                assert package_is_installed(prefix, 'toolz')

    def test_remove_spellcheck(self):
        with make_temp_env("numpy=1.12") as prefix:
            assert exists(join(prefix, PYTHON_BINARY))
            assert package_is_installed(prefix, 'numpy')

            with pytest.raises(PackagesNotFoundError) as exc:
                run_command(Commands.REMOVE, prefix, 'numpi')

            exc_string = '%r' % exc.value
            assert exc_string.strip() == dals("""
            PackagesNotFoundError: The following packages are missing from the target environment:
              - numpi
            """).strip()
            assert package_is_installed(prefix, 'numpy')

    def test_conda_list_json(self):
        def pkg_info(s):
            # function from nb_conda/envmanager.py
            if hasattr(s, 'rsplit'):  # proxy for isinstance(s, six.string_types)
                name, version, build = s.rsplit('-', 2)
                return {
                    'name': name,
                    'version': version,
                    'build': build
                }
            else:
                return {
                    'name': s['name'],
                    'version': s['version'],
                    'build': s.get('build_string') or s['build']
                }

        with make_temp_env("python=3") as prefix:
            stdout, stderr, _ = run_command(Commands.LIST, prefix, '--json')
            stdout_json = json.loads(stdout)
            packages = [pkg_info(package) for package in stdout_json]
            python_package = next(p for p in packages if p['name'] == 'python')
            assert python_package['version'].startswith('3')

    @pytest.mark.skipif(context.subdir == "win-32", reason="dependencies not available for win-32")
    def test_legacy_repodata(self):
        channel = join(dirname(abspath(__file__)), 'data', 'legacy_repodata')
        with make_temp_env('python', 'moto=1.3.7', '-c', channel, '--no-deps') as prefix:
            assert exists(join(prefix, PYTHON_BINARY))
            assert package_is_installed(prefix, 'moto=1.3.7')

    @pytest.mark.skipif(context.subdir == "win-32", reason="dependencies not available for win-32")
    def test_cross_channel_incompatibility(self):
        # regression test for https://github.com/conda/conda/issues/8772
        # conda-forge puts a run_constrains on libboost, which they don't have on conda-forge.
        #   This is a way of forcing libboost to be removed.  It's a way that they achieve
        #   mutual exclusivity with the boost from defaults that works differently.

        # if this test passes, we'll hit the DryRunExit exception, instead of an UnsatisfiableError
        with pytest.raises(DryRunExit):
            stdout, stderr, _ = run_command(Commands.CREATE, "dummy_channel_incompat_test",
                                            '--dry-run', '-c', 'conda-forge', 'python',
                                            'boost==1.70.0', 'boost-cpp==1.70.0', no_capture=True)

    # https://github.com/conda/conda/issues/9124
    @pytest.mark.skipif(context.subdir != 'linux-64', reason="lazy; package constraint here only valid on linux-64")
    def test_neutering_of_historic_specs(self):
        with make_temp_env('psutil=5.6.3=py37h7b6447c_0') as prefix:
            stdout, stderr, _ = run_command(Commands.INSTALL, prefix, "python=3.6")
            with open(os.path.join(prefix, 'conda-meta', 'history')) as f:
                d = f.read()
            assert re.search(r"neutered specs:.*'psutil==5.6.3'\]", d)
            # this would be unsatisfiable if the neutered specs were not being factored in correctly.
            #    If this command runs successfully (does not raise), then all is well.
            stdout, stderr, _ = run_command(Commands.INSTALL, prefix, "imagesize")

    # https://github.com/conda/conda/issues/10116
    @pytest.mark.skipif(not context.subdir.startswith('linux'), reason="__glibc only available on linux")
    def test_install_bound_virtual_package(self):
        with make_temp_env("__glibc>0") as prefix:
            pass

    @pytest.mark.integration
    def test_remove_empty_env(self):
        with make_temp_env() as prefix:
            run_command(Commands.CREATE, prefix)
            run_command(Commands.REMOVE, prefix, '--all')

    def test_remove_ignore_nonenv(self):
        with tempdir() as test_root:
            prefix = join(test_root, "not-an-env")
            filename = join(prefix, "file.dat")

            os.mkdir(prefix)
            with open(filename, "wb") as empty:
                pass

            with pytest.raises(DirectoryNotACondaEnvironmentError):
                run_command(Commands.REMOVE, prefix, "--all")

            assert(exists(filename))
            assert(exists(prefix))


@pytest.mark.skipif(True, reason="get the rest of Solve API worked out first")
@pytest.mark.integration
class PrivateEnvIntegrationTests(TestCase):

    def setUp(self):
        PackageCacheData.clear()

        self.pkgs_dirs = ','.join(context.pkgs_dirs)
        self.prefix = create_temp_location()
        run_command(Commands.CREATE, self.prefix)

        self.preferred_env = "_spiffy-test-app_"
        self.preferred_env_prefix = join(self.prefix, 'envs', self.preferred_env)

        # self.save_path_conflict = os.environ.get('CONDA_PATH_CONFLICT')
        self.saved_values = {}
        self.saved_values['CONDA_ROOT_PREFIX'] = os.environ.get('CONDA_ROOT_PREFIX')
        self.saved_values['CONDA_PKGS_DIRS'] = os.environ.get('CONDA_PKGS_DIRS')
        self.saved_values['CONDA_ENABLE_PRIVATE_ENVS'] = os.environ.get('CONDA_ENABLE_PRIVATE_ENVS')

        # os.environ['CONDA_PATH_CONFLICT'] = 'prevent'
        os.environ['CONDA_ROOT_PREFIX'] = self.prefix
        os.environ['CONDA_PKGS_DIRS'] = self.pkgs_dirs
        os.environ['CONDA_ENABLE_PRIVATE_ENVS'] = 'true'

        reset_context()

    def tearDown(self):
        rm_rf(self.prefix)

        for key, value in iteritems(self.saved_values):
            if value is not None:
                os.environ[key] = value
            else:
                del os.environ[key]

        reset_context()

    def exe_file(self, prefix, exe_name):
        if on_win:
            exe_name = exe_name + '.exe'
        return join(prefix, get_bin_directory_short_path(), exe_name)

    @patch.object(Context, 'prefix_specified')
    def test_simple_install_uninstall(self, prefix_specified):
        prefix_specified.__get__ = Mock(return_value=False)

        # >> simple progression install then uninstall <<
        run_command(Commands.INSTALL, self.prefix, "-c", "conda-test", "spiffy-test-app")
        assert not package_is_installed(self.prefix, "spiffy-test-app")
        assert isfile(self.exe_file(self.prefix, 'spiffy-test-app'))
        assert package_is_installed(self.preferred_env_prefix, "spiffy-test-app")
        with env_var('YABBA-DABBA', 'doo'):
            stdout, stderr, rc = subprocess_call_with_clean_env(self.exe_file(self.prefix, 'spiffy-test-app'))
        assert not stderr
        assert rc == 0
        json_d = json.loads(stdout)
        assert json_d['YABBA-DABBA'] == 'doo'

        run_command(Commands.INSTALL, self.prefix, "-c", "conda-test", "uses-spiffy-test-app")
        assert not package_is_installed(self.prefix, "uses-spiffy-test-app")
        assert package_is_installed(self.preferred_env_prefix, "uses-spiffy-test-app")

        run_command(Commands.REMOVE, self.prefix, "uses-spiffy-test-app")
        assert not package_is_installed(self.preferred_env_prefix, "uses-spiffy-test-app")

        run_command(Commands.REMOVE, self.prefix, "spiffy-test-app")
        assert not package_is_installed(self.prefix, "spiffy-test-app")
        assert not isfile(self.exe_file(self.prefix, 'spiffy-test-app'))
        assert not package_is_installed(self.preferred_env_prefix, "spiffy-test-app")
        assert not isfile(self.exe_file(self.preferred_env_prefix, 'spiffy-test-app'))

    @patch.object(Context, 'prefix_specified')
    def test_install_dep_uninstall_base(self, prefix_specified):
        prefix_specified.__get__ = Mock(return_value=False)

        # >> install uses-spiffy-test-app, uninstall spiffy-test-app <<
        run_command(Commands.INSTALL, self.prefix, "-c", "conda-test", "uses-spiffy-test-app")
        assert package_is_installed(self.preferred_env_prefix, "spiffy-test-app")
        assert package_is_installed(self.preferred_env_prefix, "uses-spiffy-test-app")
        assert not package_is_installed(self.prefix, "spiffy-test-app")
        assert not package_is_installed(self.prefix, "uses-spiffy-test-app")

        with pytest.raises(PackagesNotFoundError):
            run_command(Commands.REMOVE, self.prefix, "spiffy-test-app")
        assert package_is_installed(self.preferred_env_prefix, "spiffy-test-app")
        assert isfile(self.exe_file(self.preferred_env_prefix, 'spiffy-test-app'))
        assert package_is_installed(self.preferred_env_prefix, "uses-spiffy-test-app")
        assert not package_is_installed(self.prefix, "spiffy-test-app")
        assert not isfile(self.exe_file(self.prefix, 'spiffy-test-app'))

        run_command(Commands.REMOVE, self.prefix, "uses-spiffy-test-app")
        assert not package_is_installed(self.preferred_env_prefix, "uses-spiffy-test-app")

        # this part tests that the private environment was fully pruned
        assert not package_is_installed(self.preferred_env_prefix, "spiffy-test-app")
        assert not isfile(self.exe_file(self.preferred_env_prefix, 'spiffy-test-app'))

    @patch.object(Context, 'prefix_specified')
    def test_install_base_1_then_update(self, prefix_specified):
        prefix_specified.__get__ = Mock(return_value=False)

        # >> install spiffy-test-app 1.0, then update <<
        run_command(Commands.INSTALL, self.prefix, "-c", "conda-test", "spiffy-test-app=1")
        assert package_is_installed(self.prefix, "spiffy-test-app")

        run_command(Commands.UPDATE, self.prefix, "-c", "conda-test", "spiffy-test-app")
        assert not package_is_installed(self.prefix, "spiffy-test-app")
        assert package_is_installed(self.preferred_env_prefix, "spiffy-test-app")

        run_command(Commands.REMOVE, self.prefix, "spiffy-test-app")
        assert not package_is_installed(self.preferred_env_prefix, "spiffy-test-app")

    @patch.object(Context, 'prefix_specified')
    def test_install_base_then_remove_from_private_env(self, prefix_specified):
        prefix_specified.__get__ = Mock(return_value=False)

        # >> install spiffy-test-app, then remove from preferred env <<
        run_command(Commands.INSTALL, self.prefix, "-c", "conda-test", "spiffy-test-app")
        assert package_is_installed(self.preferred_env_prefix, "spiffy-test-app")

        run_command(Commands.REMOVE, self.preferred_env_prefix, "spiffy-test-app")
        assert not package_is_installed(self.prefix, "spiffy-test-app")
        assert not isfile(self.exe_file(self.prefix, 'spiffy-test-app'))
        assert not package_is_installed(self.preferred_env_prefix, "spiffy-test-app")
        assert not isfile(self.exe_file(self.preferred_env_prefix, 'spiffy-test-app'))

    @patch.object(Context, 'prefix_specified')
    def test_install_base_1_then_install_base_2(self, prefix_specified):
        prefix_specified.__get__ = Mock(return_value=False)

        # >> install spiffy-test-app 1.0, then install spiffy-test-app 2.0 <<
        run_command(Commands.INSTALL, self.prefix, "-c", "conda-test", "spiffy-test-app=1")
        assert package_is_installed(self.prefix, "spiffy-test-app")

        run_command(Commands.INSTALL, self.prefix, "-c", "conda-test", "spiffy-test-app=2")
        assert not package_is_installed(self.prefix, "spiffy-test-app")
        assert package_is_installed(self.preferred_env_prefix, "spiffy-test-app")

        run_command(Commands.REMOVE, self.prefix, "spiffy-test-app")
        assert not package_is_installed(self.preferred_env_prefix, "spiffy-test-app")

    @patch.object(Context, 'prefix_specified')
    def test_install_base_2_then_install_base_1(self, prefix_specified):
        prefix_specified.__get__ = Mock(return_value=False)

        # >> install spiffy-test-app 2.0, then spiffy-test-app 1.0 <<
        run_command(Commands.INSTALL, self.prefix, "-c", "conda-test", "spiffy-test-app")
        assert package_is_installed(self.preferred_env_prefix, "spiffy-test-app")

        run_command(Commands.INSTALL, self.prefix, "-c", "conda-test", "spiffy-test-app=1")
        assert not package_is_installed(self.preferred_env_prefix, "spiffy-test-app")
        assert package_is_installed(self.prefix, "spiffy-test-app")

    @patch.object(Context, 'prefix_specified')
    def test_install_base_2_then_install_dep_1(self, prefix_specified):
        prefix_specified.__get__ = Mock(return_value=False)

        # install spiffy-test-app 2.0, then uses-spiffy-test-app 1.0,
        #   which should suck spiffy-test-app back to the root prefix
        run_command(Commands.INSTALL, self.prefix, "-c", "conda-test", "spiffy-test-app")
        assert package_is_installed(self.preferred_env_prefix, "spiffy-test-app")
        assert not package_is_installed(self.prefix, "spiffy-test-app")
        assert not package_is_installed(self.prefix, "uses-spiffy-test-app")
        assert not package_is_installed(self.preferred_env_prefix, "uses-spiffy-test-app")

        run_command(Commands.INSTALL, self.prefix, "-c", "conda-test", "uses-spiffy-test-app=1")
        assert package_is_installed(self.prefix, "spiffy-test-app-2")
        assert package_is_installed(self.prefix, "uses-spiffy-test-app")
        assert not package_is_installed(self.preferred_env_prefix, "spiffy-test-app")
        assert not package_is_installed(self.preferred_env_prefix, "uses-spiffy-test-app")

    @patch.object(Context, 'prefix_specified')
    def test_install_dep_2_then_install_base_1(self, prefix_specified):
        prefix_specified.__get__ = Mock(return_value=False)

        # install uses-spiffy-test-app 2.0, then spiffy-test-app 1.0,
        run_command(Commands.INSTALL, self.prefix, "-c", "conda-test", "uses-spiffy-test-app")
        assert package_is_installed(self.preferred_env_prefix, "uses-spiffy-test-app")
        assert package_is_installed(self.preferred_env_prefix, "spiffy-test-app")
        assert not isfile(self.exe_file(self.prefix, 'spiffy-test-app'))

        run_command(Commands.INSTALL, self.prefix, "-c", "conda-test", "spiffy-test-app=1")
        assert package_is_installed(self.preferred_env_prefix, "spiffy-test-app=2")
        assert package_is_installed(self.preferred_env_prefix, "uses-spiffy-test-app=2")
        assert package_is_installed(self.prefix, "spiffy-test-app=1")
        assert isfile(self.exe_file(self.prefix, 'spiffy-test-app'))

    @patch.object(Context, 'prefix_specified')
    def test_install_base_1_dep_2_together(self, prefix_specified):
        prefix_specified.__get__ = Mock(return_value=False)

        run_command(Commands.INSTALL, self.prefix, "-c", "conda-test", "spiffy-test-app=1", "uses-spiffy-test-app")
        assert package_is_installed(self.preferred_env_prefix, "spiffy-test-app=2")
        assert package_is_installed(self.preferred_env_prefix, "uses-spiffy-test-app=2")
        assert package_is_installed(self.prefix, "spiffy-test-app-1")

    @patch.object(Context, 'prefix_specified')
    def test_a2(self, prefix_specified):
        prefix_specified.__get__ = Mock(return_value=False)

        run_command(Commands.INSTALL, self.prefix, "-c", "conda-test", "uses-spiffy-test-app")
        assert package_is_installed(self.preferred_env_prefix, "spiffy-test-app=2")
        assert package_is_installed(self.preferred_env_prefix, "uses-spiffy-test-app=2")
        assert not isfile(self.exe_file(self.prefix, 'spiffy-test-app'))
        assert isfile(self.exe_file(self.preferred_env_prefix, 'spiffy-test-app'))

        run_command(Commands.INSTALL, self.prefix, "-c", "conda-test", "needs-spiffy-test-app")
        assert package_is_installed(self.preferred_env_prefix, "spiffy-test-app=2")
        assert package_is_installed(self.preferred_env_prefix, "uses-spiffy-test-app=2")
        assert package_is_installed(self.prefix, "needs-spiffy-test-app")
        assert not package_is_installed(self.prefix, "uses-spiffy-test-app=2")
        assert isfile(self.exe_file(self.prefix, 'spiffy-test-app'))
        assert isfile(self.exe_file(self.preferred_env_prefix, 'spiffy-test-app'))

        run_command(Commands.REMOVE, self.prefix, "uses-spiffy-test-app")
        assert not package_is_installed(self.preferred_env_prefix, "spiffy-test-app=2")
        assert not package_is_installed(self.preferred_env_prefix, "uses-spiffy-test-app=2")
        assert package_is_installed(self.prefix, "needs-spiffy-test-app")
        assert not package_is_installed(self.prefix, "uses-spiffy-test-app=2")
        assert isfile(self.exe_file(self.prefix, 'spiffy-test-app'))
        assert not isfile(self.exe_file(self.preferred_env_prefix, 'spiffy-test-app'))

        run_command(Commands.REMOVE, self.prefix, "needs-spiffy-test-app")
        assert not package_is_installed(self.prefix, "needs-spiffy-test-app")
        assert package_is_installed(self.prefix, "spiffy-test-app-2")
        assert isfile(self.exe_file(self.prefix, 'spiffy-test-app'))

    @patch.object(Context, 'prefix_specified')
    def test_b2(self, prefix_specified):
        prefix_specified.__get__ = Mock(return_value=False)

        run_command(Commands.INSTALL, self.prefix, "-c", "conda-test", "spiffy-test-app", "uses-spiffy-test-app")
        assert package_is_installed(self.preferred_env_prefix, "spiffy-test-app=2")
        assert package_is_installed(self.preferred_env_prefix, "uses-spiffy-test-app")
        assert isfile(self.exe_file(self.prefix, 'spiffy-test-app'))

        run_command(Commands.INSTALL, self.prefix, "-c", "conda-tes", "needs-spiffy-test-app")
        assert not package_is_installed(self.preferred_env_prefix, "spiffy-test-app=2")
        assert not package_is_installed(self.preferred_env_prefix, "uses-spiffy-test-app=2")
        assert package_is_installed(self.prefix, "needs-spiffy-test-app")
        assert package_is_installed(self.prefix, "spiffy-test-app=2")
        assert package_is_installed(self.prefix, "uses-spiffy-test-app")

    @patch.object(Context, 'prefix_specified')
    def test_c2(self, prefix_specified):
        prefix_specified.__get__ = Mock(return_value=False)

        run_command(Commands.INSTALL, self.prefix, "-c", "conda-test", "needs-spiffy-test-app")
        assert package_is_installed(self.prefix, "spiffy-test-app=2")
        assert package_is_installed(self.prefix, "needs-spiffy-test-app")
        assert not package_is_installed(self.preferred_env_prefix, "spiffy-test-app=2")

        run_command(Commands.INSTALL, self.prefix, "-c", "conda-test", "spiffy-test-app=2")  # nothing to do
        assert package_is_installed(self.prefix, "spiffy-test-app=2")
        assert package_is_installed(self.prefix, "needs-spiffy-test-app")
        assert not package_is_installed(self.preferred_env_prefix, "spiffy-test-app=2")

    @patch.object(Context, 'prefix_specified')
    def test_d2(self, prefix_specified):
        prefix_specified.__get__ = Mock(return_value=False)

        run_command(Commands.INSTALL, self.prefix, "-c", "conda-test", "spiffy-test-app")
        assert package_is_installed(self.preferred_env_prefix, "spiffy-test-app=2")
        assert isfile(self.exe_file(self.prefix, 'spiffy-test-app'))
        assert isfile(self.exe_file(self.preferred_env_prefix, 'spiffy-test-app'))

        run_command(Commands.INSTALL, self.prefix, "-c", "conda-test", "needs-spiffy-test-app")
        assert not package_is_installed(self.preferred_env_prefix, "spiffy-test-app=2")
        assert package_is_installed(self.prefix, "spiffy-test-app=2")
        assert package_is_installed(self.prefix, "needs-spiffy-test-app")
        assert not isfile(self.exe_file(self.preferred_env_prefix, 'spiffy-test-app'))
