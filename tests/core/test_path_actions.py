# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import importlib.util
import os
import sys
from logging import getLogger
from os.path import basename, dirname, getsize, isdir, isfile, join, lexists
from pathlib import Path
from uuid import uuid4

import pytest

from conda.auxlib.collection import AttrDict
from conda.auxlib.ish import dals
from conda.base.context import context
from conda.common.compat import on_win
from conda.common.iterators import groupby_to_dict as groupby
from conda.common.path import (
    get_bin_directory_short_path,
    get_python_noarch_target_path,
    get_python_short_path,
    get_python_site_packages_short_path,
    parse_entry_point_def,
    pyc_path,
    win_path_ok,
)
from conda.core.path_actions import (
    CompileMultiPycAction,
    CreatePythonEntryPointAction,
    LinkPathAction,
)
from conda.gateways.disk.create import create_link, mkdir_p
from conda.gateways.disk.delete import rm_rf
from conda.gateways.disk.link import islink
from conda.gateways.disk.permissions import is_executable
from conda.gateways.disk.read import compute_sum
from conda.gateways.disk.test import softlink_supported
from conda.models.enums import LinkType, NoarchType, PathType
from conda.models.records import PathDataV1
from conda.testing import PathFactoryFixture

log = getLogger(__name__)


def make_test_file(target_dir, suffix="", contents=""):
    if not isdir(target_dir):
        mkdir_p(target_dir)
    fn = str(uuid4())[:8]
    full_path = join(target_dir, fn + suffix)
    with open(full_path, "w") as fh:
        fh.write(contents or str(uuid4()))
    return full_path


def load_python_file(py_file_full_path):
    spec = importlib.util.spec_from_file_location("module.name", py_file_full_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def prefix(path_factory: PathFactoryFixture) -> Path:
    path = path_factory(prefix=uuid4().hex[:8], name=" ", suffix=uuid4().hex[:8])
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture
def pkgs_dir(path_factory: PathFactoryFixture) -> Path:
    path = path_factory(prefix=uuid4().hex[:8], name=" ", suffix=uuid4().hex[:8])
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_CompileMultiPycAction_generic(prefix: Path):
    package_info = AttrDict(
        package_metadata=AttrDict(noarch=AttrDict(type=NoarchType.generic))
    )
    noarch = package_info.package_metadata and package_info.package_metadata.noarch
    assert noarch.type == NoarchType.generic
    axns = CompileMultiPycAction.create_actions({}, package_info, prefix, None, ())
    assert axns == ()

    package_info = AttrDict(package_metadata=None)
    axns = CompileMultiPycAction.create_actions({}, package_info, prefix, None, ())
    assert axns == ()


@pytest.mark.xfail(on_win, reason="pyc compilation need env on windows, see gh #8025")
def test_CompileMultiPycAction_noarch_python(prefix: Path):
    if not softlink_supported(__file__, prefix) and on_win:
        pytest.skip("softlink not supported")
    target_python_version = "%d.%d" % sys.version_info[:2]
    sp_dir = get_python_site_packages_short_path(target_python_version)
    transaction_context = {
        "target_python_version": target_python_version,
        "target_site_packages_short_path": sp_dir,
    }
    package_info = AttrDict(
        package_metadata=AttrDict(noarch=AttrDict(type=NoarchType.python))
    )

    file_link_actions = [
        AttrDict(
            source_short_path="site-packages/something.py",
            target_short_path=get_python_noarch_target_path(
                "site-packages/something.py", sp_dir
            ),
        ),
        AttrDict(
            source_short_path="site-packages/another.py",
            target_short_path=get_python_noarch_target_path(
                "site-packages/another.py", sp_dir
            ),
        ),
        AttrDict(
            # this one shouldn't get compiled
            source_short_path="something.py",
            target_short_path=get_python_noarch_target_path("something.py", sp_dir),
        ),
        AttrDict(
            # this one shouldn't get compiled
            source_short_path="another.py",
            target_short_path=get_python_noarch_target_path("another.py", sp_dir),
        ),
    ]
    axns = CompileMultiPycAction.create_actions(
        transaction_context, package_info, str(prefix), None, file_link_actions
    )

    assert len(axns) == 1
    axn = axns[0]
    source_full_paths = tuple(axn.source_full_paths)
    source_full_path0 = source_full_paths[0]
    source_full_path1 = source_full_paths[1]
    assert len(source_full_paths) == 2
    assert source_full_path0 == join(
        prefix,
        win_path_ok(
            get_python_noarch_target_path("site-packages/something.py", sp_dir)
        ),
    )
    assert source_full_path1 == join(
        prefix,
        win_path_ok(get_python_noarch_target_path("site-packages/another.py", sp_dir)),
    )
    target_full_paths = tuple(axn.target_full_paths)
    target_full_path0 = target_full_paths[0]
    target_full_path1 = target_full_paths[1]
    assert len(target_full_paths) == 2
    assert target_full_path0 == join(
        prefix,
        win_path_ok(
            pyc_path(
                get_python_noarch_target_path("site-packages/something.py", sp_dir),
                target_python_version,
            )
        ),
    )
    assert target_full_path1 == join(
        prefix,
        win_path_ok(
            pyc_path(
                get_python_noarch_target_path("site-packages/another.py", sp_dir),
                target_python_version,
            )
        ),
    )

    # make .py file in prefix that will be compiled
    mkdir_p(dirname(source_full_path0))
    with open(source_full_path0, "w") as fh:
        fh.write("value = 42\n")
    mkdir_p(dirname(source_full_path1))
    with open(source_full_path1, "w") as fh:
        fh.write("value = 43\n")

    # symlink the current python
    python_full_path = join(prefix, get_python_short_path(target_python_version))
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

    imported_pyc_file = load_python_file(target_full_path0)
    assert imported_pyc_file.value == 42
    imported_pyc_file = load_python_file(target_full_path1)
    assert imported_pyc_file.value == 43

    axn.reverse()
    assert not isfile(target_full_path0)
    assert not isfile(target_full_path1)


def test_CreatePythonEntryPointAction_generic(prefix: Path):
    package_info = AttrDict(package_metadata=None)
    axns = CreatePythonEntryPointAction.create_actions({}, package_info, prefix, None)
    assert axns == ()


def test_CreatePythonEntryPointAction_noarch_python(prefix: Path):
    target_python_version = "%d.%d" % sys.version_info[:2]
    transaction_context = {
        "target_python_version": target_python_version,
    }
    package_info = AttrDict(
        package_metadata=AttrDict(
            noarch=AttrDict(
                type=NoarchType.python,
                entry_points=(
                    "command1=some.module:main",
                    "command2=another.somewhere:go",
                ),
            )
        )
    )

    axns = CreatePythonEntryPointAction.create_actions(
        transaction_context, package_info, prefix, LinkType.hardlink
    )
    grouped_axns = groupby(lambda ax: isinstance(ax, LinkPathAction), axns)
    windows_exe_axns = grouped_axns.get(True, ())
    assert len(windows_exe_axns) == (2 if on_win else 0)
    py_ep_axns = grouped_axns.get(False, ())
    assert len(py_ep_axns) == 2

    py_ep_axn = py_ep_axns[0]

    command, module, func = parse_entry_point_def("command1=some.module:main")
    assert command == "command1"
    if on_win:
        target_short_path = f"{get_bin_directory_short_path()}\\{command}-script.py"
    else:
        target_short_path = f"{get_bin_directory_short_path()}/{command}"
    assert py_ep_axn.target_full_path == join(prefix, target_short_path)
    assert py_ep_axn.module == module == "some.module"
    assert py_ep_axn.func == func == "main"

    mkdir_p(dirname(py_ep_axn.target_full_path))
    py_ep_axn.execute()
    assert isfile(py_ep_axn.target_full_path)
    if not on_win:
        assert is_executable(py_ep_axn.target_full_path)
    with open(py_ep_axn.target_full_path) as fh:
        lines = fh.read()
        last_line = lines.splitlines()[-1].strip()
    if not on_win:
        python_full_path = join(prefix, get_python_short_path(target_python_version))
        if " " in str(prefix):
            # spaces in prefix break shebang! we use this python/shell workaround
            # also seen in virtualenv
            assert lines.startswith(
                dals(
                    f"""
                    #!/bin/sh
                    '''exec' "{python_full_path}" "$0" "$@" #'''
                    """
                )
            )
        else:
            assert lines.startswith(f"#!{python_full_path}\n")
    assert last_line == "sys.exit(%s())" % func

    py_ep_axn.reverse()
    assert not isfile(py_ep_axn.target_full_path)

    if on_win:
        windows_exe_axn = windows_exe_axns[0]
        target_short_path = f"{get_bin_directory_short_path()}\\{command}.exe"
        assert windows_exe_axn.target_full_path == join(prefix, target_short_path)

        mkdir_p(dirname(windows_exe_axn.target_full_path))
        windows_exe_axn.verify()
        windows_exe_axn.execute()
        assert isfile(windows_exe_axn.target_full_path)
        assert is_executable(windows_exe_axn.target_full_path)

        src = compute_sum(join(context.conda_prefix, "Scripts/conda.exe"), "md5")
        assert src == compute_sum(windows_exe_axn.target_full_path, "md5")

        windows_exe_axn.reverse()
        assert not isfile(windows_exe_axn.target_full_path)


def test_simple_LinkPathAction_hardlink(prefix: Path, pkgs_dir: Path):
    source_full_path = make_test_file(pkgs_dir)
    target_short_path = source_short_path = basename(source_full_path)

    correct_sha256 = compute_sum(source_full_path, "sha256")
    correct_size_in_bytes = getsize(source_full_path)
    path_type = PathType.hardlink

    source_path_data = PathDataV1(
        _path=source_short_path,
        path_type=path_type,
        sha256=correct_sha256,
        size_in_bytes=correct_size_in_bytes,
    )

    axn = LinkPathAction(
        {},
        None,
        pkgs_dir,
        source_short_path,
        prefix,
        target_short_path,
        LinkType.hardlink,
        source_path_data,
    )

    assert axn.target_full_path == join(prefix, target_short_path)
    axn.verify()
    axn.execute()
    assert isfile(axn.target_full_path)
    assert not islink(axn.target_full_path)
    assert os.lstat(axn.target_full_path).st_nlink == 2

    axn.reverse()
    assert not lexists(axn.target_full_path)


def test_simple_LinkPathAction_softlink(prefix: Path, pkgs_dir: Path):
    if not softlink_supported(__file__, prefix) and on_win:
        pytest.skip("softlink not supported")

    source_full_path = make_test_file(pkgs_dir)
    target_short_path = source_short_path = basename(source_full_path)

    correct_sha256 = compute_sum(source_full_path, "sha256")
    correct_size_in_bytes = getsize(source_full_path)
    path_type = PathType.hardlink

    source_path_data = PathDataV1(
        _path=source_short_path,
        path_type=path_type,
        sha256=correct_sha256,
        size_in_bytes=correct_size_in_bytes,
    )

    axn = LinkPathAction(
        {},
        None,
        pkgs_dir,
        source_short_path,
        prefix,
        target_short_path,
        LinkType.softlink,
        source_path_data,
    )

    assert axn.target_full_path == join(prefix, target_short_path)
    axn.verify()
    axn.execute()
    assert isfile(axn.target_full_path)
    assert islink(axn.target_full_path)
    assert os.lstat(axn.target_full_path).st_nlink == 1

    axn.reverse()
    assert not lexists(axn.target_full_path)
    assert lexists(source_full_path)


def test_simple_LinkPathAction_directory(prefix: Path):
    target_short_path = join("a", "nested", "directory")
    axn = LinkPathAction(
        {},
        None,
        None,
        None,
        prefix,
        target_short_path,
        LinkType.directory,
        None,
    )
    axn.verify()
    axn.execute()

    assert isdir(join(prefix, target_short_path))

    axn.reverse()
    # this is counter-intuitive, but it's faster to tell conda to ignore folders for removal in transactions
    #    than it is to try to have it scan to see if anything else has populated that folder.
    assert lexists(axn.target_full_path)
    assert lexists(dirname(axn.target_full_path))
    assert lexists(dirname(dirname(axn.target_full_path)))


def test_simple_LinkPathAction_copy(prefix: Path, pkgs_dir: Path):
    source_full_path = make_test_file(pkgs_dir)
    target_short_path = source_short_path = basename(source_full_path)

    correct_sha256 = compute_sum(source_full_path, "sha256")
    correct_size_in_bytes = getsize(source_full_path)
    path_type = PathType.hardlink

    source_path_data = PathDataV1(
        _path=source_short_path,
        path_type=path_type,
        sha256=correct_sha256,
        size_in_bytes=correct_size_in_bytes,
    )

    axn = LinkPathAction(
        {},
        None,
        pkgs_dir,
        source_short_path,
        prefix,
        target_short_path,
        LinkType.copy,
        source_path_data,
    )

    assert axn.target_full_path == join(prefix, target_short_path)
    axn.verify()
    axn.execute()
    assert isfile(axn.target_full_path)
    assert not islink(axn.target_full_path)
    assert os.lstat(axn.target_full_path).st_nlink == 1

    axn.reverse()
    assert not lexists(axn.target_full_path)
