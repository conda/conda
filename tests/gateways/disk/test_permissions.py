# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import absolute_import, division, print_function, unicode_literals

import os
import uuid

import errno
import pytest
from errno import ENOENT, EACCES, EROFS, EPERM
from shutil import rmtree
from contextlib import contextmanager
from tempfile import gettempdir
from os.path import join, isfile, lexists
from stat import S_IRUSR, S_IRGRP, S_IROTH
from stat import S_IRWXG, S_IRWXO, S_IRWXU
from stat import S_IXUSR, S_IXGRP, S_IXOTH
from conda.gateways.disk.update import touch

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch


def create_temp_location():
    tempdirdir = gettempdir()
    dirname = str(uuid.uuid4())[:8]
    return join(tempdirdir, dirname)


@contextmanager
def tempdir():
    prefix = create_temp_location()
    try:
        os.makedirs(prefix)
        yield prefix
    finally:
        if lexists(prefix):
            rmtree(prefix, ignore_errors=False, onerror=_remove_read_only)


def _remove_read_only(func, path, exc):
    excvalue = exc[1]
    if func in (os.rmdir, os.remove) and excvalue.errno == errno.EACCES:
        os.chmod(path, S_IRWXU| S_IRWXG| S_IRWXO)
        func(path)
    else:
        pass


def _make_read_only(path):
    os.chmod(path, S_IRUSR | S_IRGRP | S_IROTH)


def _can_write_file(test, content):
    try:
        with open(test, 'w+') as fh:
            fh.write(content)
            fh.close()
        if os.stat(test).st_size == 0.0:
            return False
        else:
            return True
    except Exception as e:
        eno = getattr(e, 'errono', None)
        if eno == 13:
            return False


def _try_open(path):
    try:
        f = open(path, 'a+')
    except:
        raise
    else:
        f.close()


def _can_execute(path):
    return bool(os.stat(path).st_mode & (S_IXUSR | S_IXGRP | S_IXOTH))


def test_make_writable():
    from conda.gateways.disk.permissions import make_writable
    with tempdir() as td:
        test_path = join(td, 'test_path')
        touch(test_path)
        assert isfile(test_path)
        _try_open(test_path)
        _make_read_only(test_path)
        pytest.raises((IOError, OSError), _try_open, test_path)
        make_writable(test_path)
        _try_open(test_path)
        assert _can_write_file(test_path, "welcome to the ministry of silly walks")
        os.remove(test_path)
        assert not isfile(test_path)


def test_make_writable_doesnt_exist():
    from conda.gateways.disk.permissions import make_writable
    with pytest.raises((IOError, OSError)) as exc:
        make_writable(join('some', 'path', 'that', 'definitely', 'doesnt', 'exist'))
    assert exc.value.errno == ENOENT


def test_make_writable_dir_EPERM():
    import conda.gateways.disk.permissions
    from conda.gateways.disk.permissions import make_writable
    with patch.object(conda.gateways.disk.permissions, 'chmod') as chmod_mock:
        chmod_mock.side_effect = IOError(EPERM, 'some message', 'foo')
        with tempdir() as td:
            assert not make_writable(td)


def test_make_writable_dir_EACCES():
    import conda.gateways.disk.permissions
    from conda.gateways.disk.permissions import make_writable
    with patch.object(conda.gateways.disk.permissions, 'chmod') as chmod_mock:
        chmod_mock.side_effect = IOError(EACCES, 'some message', 'foo')
        with tempdir() as td:
            assert not make_writable(td)


def test_make_writable_dir_EROFS():
    import conda.gateways.disk.permissions
    from conda.gateways.disk.permissions import make_writable
    with patch.object(conda.gateways.disk.permissions, 'chmod') as chmod_mock:
        chmod_mock.side_effect = IOError(EROFS, 'some message', 'foo')
        with tempdir() as td:
            assert not make_writable(td)


def test_recursive_make_writable():
    from conda.gateways.disk.permissions import recursive_make_writable
    with tempdir() as td:
        test_path = join(td, 'test_path')
        touch(test_path)
        assert isfile(test_path)
        _try_open(test_path)
        _make_read_only(test_path)
        pytest.raises((IOError, OSError), _try_open, test_path)
        recursive_make_writable(test_path)
        _try_open(test_path)
        assert _can_write_file(test_path, "welcome to the ministry of silly walks")
        os.remove(test_path)
        assert not isfile(test_path)


def test_make_executable():
    from conda.gateways.disk.permissions import make_executable
    with tempdir() as td:
        test_path = join(td, 'test_path')
        touch(test_path)
        assert isfile(test_path)
        _try_open(test_path)
        _make_read_only(test_path)
        assert not _can_write_file(test_path, "welcome to the ministry of silly walks")
        assert not _can_execute(test_path)
        make_executable(test_path)
