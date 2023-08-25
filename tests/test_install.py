# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import random
import subprocess
import sys
import tempfile
from os import chdir, getcwd, makedirs
from os.path import exists, join, relpath
from unittest import mock

import pytest

from conda.base.context import context
from conda.common.compat import on_win
from conda.core.package_cache_data import download
from conda.core.portability import _PaddingError, binary_replace, update_prefix
from conda.gateways.disk.delete import move_path_to_trash
from conda.gateways.disk.read import read_no_link, yield_lines
from conda.models.enums import FileMode
from conda.testing import PathFactoryFixture

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
