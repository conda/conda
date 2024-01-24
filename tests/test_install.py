# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import random
import subprocess
import sys
import tempfile
from json import loads as json_loads
from os import chdir, getcwd, makedirs
from os.path import exists, isdir, join, relpath
from pathlib import Path
from unittest import mock

import pytest
from pytest import MonkeyPatch

from conda.base.context import context, reset_context
from conda.common.compat import on_win
from conda.core.package_cache_data import download
from conda.core.portability import _PaddingError, binary_replace, update_prefix
from conda.core.prefix_data import PrefixData
from conda.exceptions import DirectoryNotACondaEnvironmentError, PackagesNotFoundError
from conda.gateways.disk.delete import move_path_to_trash, path_is_clean, rm_rf
from conda.gateways.disk.read import read_no_link, yield_lines
from conda.models.enums import FileMode
from conda.testing import CondaCLIFixture, PathFactoryFixture, TmpEnvFixture
from conda.testing.integration import package_is_installed

patch = mock.patch if mock else None


def generate_random_path():
    return "/some/path/to/file%s" % random.randint(100, 200)


@pytest.mark.xfail(on_win, reason="binary replacement on windows skipped", strict=True)
def test_simple():
    for encoding in ("utf-8", "utf-16-le", "utf-16-be", "utf-32-le", "utf-32-be"):
        a = "aaaaa".encode(encoding)
        b = "bbbb".encode(encoding)
        data = "xxxaaaaaxyz\0zz".encode(encoding)
        result = "xxxbbbbxyz\0\0zz".encode(encoding)
        assert binary_replace(data, a, b, encoding=encoding) == result


@pytest.mark.xfail(on_win, reason="binary replacement on windows skipped", strict=True)
def test_shorter():
    assert (
        binary_replace(b"xxxaaaaaxyz\x00zz", b"aaaaa", b"bbbb")
        == b"xxxbbbbxyz\x00\x00zz"
    )


@pytest.mark.xfail(on_win, reason="binary replacement on windows skipped", strict=True)
def test_too_long():
    with pytest.raises(_PaddingError):
        binary_replace(b"xxxaaaaaxyz\x00zz", b"aaaaa", b"bbbbbbbb")


@pytest.mark.xfail(on_win, reason="binary replacement on windows skipped", strict=True)
def test_no_extra():
    assert binary_replace(b"aaaaa\x00", b"aaaaa", b"bbbbb") == b"bbbbb\x00"


@pytest.mark.xfail(on_win, reason="binary replacement on windows skipped", strict=True)
def test_two():
    assert (
        binary_replace(b"aaaaa\x001234aaaaacc\x00\x00", b"aaaaa", b"bbbbb")
        == b"bbbbb\x001234bbbbbcc\x00\x00"
    )


@pytest.mark.xfail(on_win, reason="binary replacement on windows skipped", strict=True)
def test_spaces():
    assert binary_replace(b" aaaa \x00", b"aaaa", b"bbbb") == b" bbbb \x00"


@pytest.mark.xfail(on_win, reason="binary replacement on windows skipped", strict=True)
def test_multiple():
    assert binary_replace(b"aaaacaaaa\x00", b"aaaa", b"bbbb") == b"bbbbcbbbb\x00"
    assert binary_replace(b"aaaacaaaa\x00", b"aaaa", b"bbb") == b"bbbcbbb\x00\x00\x00"
    with pytest.raises(_PaddingError):
        binary_replace(b"aaaacaaaa\x00", b"aaaa", b"bbbbb")


@pytest.mark.integration
@pytest.mark.skipif(not on_win, reason="exe entry points only necessary on win")
def test_windows_entry_point():
    """
    This emulates pip-created entry point executables on windows.  For more info,
    refer to conda/install.py::replace_entry_point_shebang
    """
    tmp_dir = tempfile.mkdtemp()
    cwd = getcwd()
    chdir(tmp_dir)
    original_prefix = "C:\\BogusPrefix\\python.exe"
    try:
        url = "https://s3.amazonaws.com/conda-dev/pyzzerw.pyz"
        download(url, "pyzzerw.pyz")
        url = (
            "https://files.pythonhosted.org/packages/source/c/conda/conda-4.1.6.tar.gz"
        )
        download(url, "conda-4.1.6.tar.gz")
        subprocess.check_call(
            [
                sys.executable,
                "pyzzerw.pyz",
                # output file
                "-o",
                "conda.exe",
                # entry point
                "-m",
                "conda.cli.main:main",
                # initial shebang
                "-s",
                "#! " + original_prefix,
                # launcher executable to use (32-bit text should be compatible)
                "-l",
                "t32",
                # source archive to turn into executable
                "conda-4.1.6.tar.gz",
            ],
            cwd=tmp_dir,
        )
        # this is the actual test: change the embedded prefix and make sure that the exe runs.
        data = open("conda.exe", "rb").read()
        fixed_data = binary_replace(data, original_prefix, sys.executable)
        with open("conda.fixed.exe", "wb") as f:
            f.write(fixed_data)
        # without a valid shebang in the exe, this should fail
        with pytest.raises(subprocess.CalledProcessError):
            subprocess.check_call(["conda.exe", "-h"])

        process = subprocess.Popen(
            ["conda.fixed.exe", "-h"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        output, error = process.communicate()
        output = output.decode("utf-8")
        error = error.decode("utf-8")
        assert (
            "conda is a tool for managing and deploying applications, "
            "environments and packages."
        ) in output
    except:
        raise
    finally:
        chdir(cwd)


def test_default_text(path_factory: PathFactoryFixture):
    tmp = path_factory()
    tmp.write_text('#!/opt/anaconda1anaconda2anaconda3/bin/python\necho "Hello"\n')
    update_prefix(tmp, "/usr/local")
    assert tmp.read_text() == '#!/usr/local/bin/python\necho "Hello"\n'


@pytest.mark.skipif(on_win, reason="test is invalid on windows")
def test_long_default_text(path_factory: PathFactoryFixture):
    tmp = path_factory()
    tmp.write_text('#!/opt/anaconda1anaconda2anaconda3/bin/python -O\necho "Hello"\n')
    update_prefix(tmp, f"/usr/local/{'1234567890' * 52}")
    assert tmp.read_text() == '#!/usr/bin/env python -O\necho "Hello"\n'


@pytest.mark.skipif(on_win, reason="no binary replacement done on win")
def test_binary(path_factory: PathFactoryFixture):
    tmp = path_factory()
    tmp.write_bytes(b"\x7fELF.../some-placeholder/lib/libfoo.so\0")
    update_prefix(
        tmp,
        "/usr/local",
        placeholder="/some-placeholder",
        mode=FileMode.binary,
    )
    assert tmp.read_bytes() == b"\x7fELF.../usr/local/lib/libfoo.so\0\0\0\0\0\0\0\0"


def test_trash_outside_prefix():
    tmp_dir = tempfile.mkdtemp()
    rel = relpath(tmp_dir, context.root_prefix)
    assert rel.startswith("..")
    move_path_to_trash(tmp_dir)
    assert not exists(tmp_dir)
    makedirs(tmp_dir)
    move_path_to_trash(tmp_dir)
    assert not exists(tmp_dir)


def _make_lines_file(path):
    with open(path, "w") as fh:
        fh.write("line 1\n")
        fh.write("line 2\n")
        fh.write("# line 3\n")
        fh.write("line 4\n")


def test_yield_lines(tmpdir):
    tempfile = join(str(tmpdir), "testfile")
    _make_lines_file(tempfile)
    lines = list(yield_lines(tempfile))
    assert lines == ["line 1", "line 2", "line 4"]


def test_read_no_link(tmpdir):
    tempdir = str(tmpdir)
    no_link = join(tempdir, "no_link")
    no_softlink = join(tempdir, "no_softlink")
    _make_lines_file(no_link)
    s1 = read_no_link(tempdir)
    assert s1 == {"line 1", "line 2", "line 4"}

    _make_lines_file(no_softlink)
    s2 = read_no_link(tempdir)
    assert s2 == {"line 1", "line 2", "line 4"}


def test_install_freezes_env_by_default(
    test_recipes_channel: Path,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    # We pass --no-update-deps/--freeze-installed by default, effectively.  This helps speed things
    # up by not considering changes to existing stuff unless the solve ends up unsatisfiable.

    # create an initial env
    with tmp_env("dependent=2.0") as prefix:
        assert package_is_installed(prefix, "dependent=2.0")
        # Install a version older than the last one
        conda_cli("install", f"--prefix={prefix}", "dependent=1.0", "--yes")

        stdout, stderr, _ = conda_cli("list", f"--prefix={prefix}", "--json")

        pkgs = json_loads(stdout)

        conda_cli(
            "install",
            f"--prefix={prefix}",
            "another_dependent",
            "--freeze-installed",
            "--yes",
        )

        stdout, _, _ = conda_cli("list", f"--prefix={prefix}", "--json")
        pkgs_after_install = json_loads(stdout)

        # Compare before and after installing package
        for pkg in pkgs:
            for pkg_after in pkgs_after_install:
                if pkg["name"] == pkg_after["name"]:
                    assert pkg["version"] == pkg_after["version"]


def test_install_mkdir(tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture):
    try:
        with tmp_env() as prefix:
            file = prefix / "tempfile.txt"
            file.write_text("test")
            dir = prefix / "conda-meta"
            assert isdir(dir)
            assert exists(file)
            with pytest.raises(DirectoryNotACondaEnvironmentError):
                stdout, _, _ = conda_cli(
                    "install", f"--prefix={dir}", "python", "--mkdir", "--yes"
                )
                assert (
                    "The target directory exists, but it is not a conda environment."
                    in stdout
                )

            conda_cli("create", f"--prefix={dir}", "--yes")
            conda_cli("install", f"--prefix={dir}", "python", "--mkdir", "--yes")
            assert package_is_installed(dir, "python")

            rm_rf(prefix, clean_empty_parents=True)
            assert path_is_clean(dir)

            # this part also a regression test for #4849
            conda_cli(
                "install",
                f"--prefix={dir}",
                "python-dateutil",
                "python",
                "--mkdir",
                "--yes",
            )
            assert package_is_installed(dir, "python")
            assert package_is_installed(dir, "python-dateutil")

    finally:
        rm_rf(prefix, clean_empty_parents=True)


def test_conda_pip_interop_dependency_satisfied_by_pip(
    monkeypatch: MonkeyPatch, tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture
):
    with tmp_env("python=3.10", "pip") as prefix:
        assert package_is_installed(prefix, "python=3.10")
        assert package_is_installed(prefix, "pip")
        monkeypatch.setenv("CONDA_PIP_INTEROP_ENABLED", "true")
        reset_context()
        assert context.pip_interop_enabled
        conda_cli(
            "run",
            f"--prefix={prefix}",
            "--dev",
            "python",
            "-m",
            "pip",
            "install",
            "itsdangerous",
        )

        PrefixData._cache_.clear()
        output, error, _ = conda_cli("list", f"--prefix={prefix}")
        assert "itsdangerous" in output
        assert not error

        output, _, _ = conda_cli(
            "install",
            f"--prefix={prefix}",
            "flask",
            "--json",
        )
        json_obj = json_loads(output.strip())
        print(json_obj)
        assert any(rec["name"] == "flask" for rec in json_obj["actions"]["LINK"])
        assert not any(
            rec["name"] == "itsdangerous" for rec in json_obj["actions"]["LINK"]
        )

    with pytest.raises(PackagesNotFoundError):
        output, _, _ = conda_cli(
            "search",
            "not-a-real-package",
            "--json",
        )
        json_obj = json_loads(output.strip())
        assert not len(json_obj.keys()) == 0
