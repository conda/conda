# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger

from conda.common.path import (get_major_minor_version, missing_pyc_files, url_to_path,
                               win_path_backout)

log = getLogger(__name__)


def test_url_to_path_unix():
    assert url_to_path("file:///etc/fstab") == "/etc/fstab"
    assert url_to_path("file://localhost/etc/fstab") == "/etc/fstab"
    assert url_to_path("file://127.0.0.1/etc/fstab") == "/etc/fstab"
    assert url_to_path("file://::1/etc/fstab") == "/etc/fstab"


def test_url_to_path_windows_local():
    assert url_to_path("file:///c|/WINDOWS/notepad.exe") == "c:/WINDOWS/notepad.exe"
    assert url_to_path("file:///C:/WINDOWS/notepad.exe") == "C:/WINDOWS/notepad.exe"
    assert url_to_path("file://localhost/C|/WINDOWS/notepad.exe") == "C:/WINDOWS/notepad.exe"
    assert url_to_path("file://localhost/c:/WINDOWS/notepad.exe") == "c:/WINDOWS/notepad.exe"
    assert url_to_path("C:\\Windows\\notepad.exe") == "C:\\Windows\\notepad.exe"
    assert url_to_path("file:///C:/Program%20Files/Internet%20Explorer/iexplore.exe") == "C:/Program Files/Internet Explorer/iexplore.exe"
    assert url_to_path("C:\\Program Files\\Internet Explorer\\iexplore.exe") == "C:\\Program Files\\Internet Explorer\\iexplore.exe"


def test_url_to_path_windows_unc():
    assert url_to_path("file://windowshost/windowshare/path") == "//windowshost/windowshare/path"
    assert url_to_path("\\\\windowshost\\windowshare\\path") == "\\\\windowshost\\windowshare\\path"
    assert url_to_path("file://windowshost\\windowshare\\path") == "//windowshost\\windowshare\\path"
    assert url_to_path("file://\\\\machine\\shared_folder\\path\\conda") == "\\\\machine\\shared_folder\\path\\conda"


def test_win_path_backout():
    assert win_path_backout("file://\\\\machine\\shared_folder\\path\\conda") == "file://machine/shared_folder/path/conda"
    assert win_path_backout("file://\\\\machine\\shared\\ folder\\path\\conda") == "file://machine/shared\\ folder/path/conda"


FILES = (
    "bin/flask",
    "lib/python2.7/site-packages/Flask-0.11.1-py2.7.egg-info/PKG-INFO",
    "lib/python2.7/site-packages/Flask-0.11.1-py2.7.egg-info/SOURCES.txt",
    "lib/python2.7/site-packages/Flask-0.11.1-py2.7.egg-info/dependency_links.txt",
    "lib/python2.7/site-packages/Flask-0.11.1-py2.7.egg-info/entry_points.txt",
    "lib/python2.7/site-packages/Flask-0.11.1-py2.7.egg-info/not-zip-safe",
    "lib/python2.7/site-packages/Flask-0.11.1-py2.7.egg-info/requires.txt",
    "lib/python2.7/site-packages/Flask-0.11.1-py2.7.egg-info/top_level.txt",
    "lib/python2.7/site-packages/flask/__init__.py",
    "lib/python2.7/site-packages/flask/__main__.py",
    "lib/python2.7/site-packages/flask/_compat.py",
    "lib/python2.7/site-packages/flask/app.py",
    "lib/python2.7/site-packages/flask/blueprints.py",
    "lib/python2.7/site-packages/flask/cli.py",
    "lib/python2.7/site-packages/flask/config.py",
    "lib/python2.7/site-packages/flask/ctx.py",
    "lib/python2.7/site-packages/flask/debughelpers.py",
    "lib/python2.7/site-packages/flask/ext/__init__.py",
)


def test_missing_pyc_files_27():
    missing = missing_pyc_files('27', FILES)
    assert len(missing) == 10
    assert tuple(m[1] for m in missing) == (
        "lib/python2.7/site-packages/flask/__init__.pyc",
        "lib/python2.7/site-packages/flask/__main__.pyc",
        "lib/python2.7/site-packages/flask/_compat.pyc",
        "lib/python2.7/site-packages/flask/app.pyc",
        "lib/python2.7/site-packages/flask/blueprints.pyc",
        "lib/python2.7/site-packages/flask/cli.pyc",
        "lib/python2.7/site-packages/flask/config.pyc",
        "lib/python2.7/site-packages/flask/ctx.pyc",
        "lib/python2.7/site-packages/flask/debughelpers.pyc",
        "lib/python2.7/site-packages/flask/ext/__init__.pyc",
    )


def test_missing_pyc_files_34():
    missing = missing_pyc_files('34', FILES)
    assert len(missing) == 10
    assert tuple(m[1] for m in missing) == (
        "lib/python2.7/site-packages/flask/__pycache__/__init__.cpython-34.pyc",
        "lib/python2.7/site-packages/flask/__pycache__/__main__.cpython-34.pyc",
        "lib/python2.7/site-packages/flask/__pycache__/_compat.cpython-34.pyc",
        "lib/python2.7/site-packages/flask/__pycache__/app.cpython-34.pyc",
        "lib/python2.7/site-packages/flask/__pycache__/blueprints.cpython-34.pyc",
        "lib/python2.7/site-packages/flask/__pycache__/cli.cpython-34.pyc",
        "lib/python2.7/site-packages/flask/__pycache__/config.cpython-34.pyc",
        "lib/python2.7/site-packages/flask/__pycache__/ctx.cpython-34.pyc",
        "lib/python2.7/site-packages/flask/__pycache__/debughelpers.cpython-34.pyc",
        "lib/python2.7/site-packages/flask/ext/__pycache__/__init__.cpython-34.pyc",
    )


def test_missing_pyc_files_35():
    missing = missing_pyc_files('35', FILES)
    assert len(missing) == 10
    assert tuple(m[1] for m in missing) == (
        "lib/python2.7/site-packages/flask/__pycache__/__init__.cpython-35.pyc",
        "lib/python2.7/site-packages/flask/__pycache__/__main__.cpython-35.pyc",
        "lib/python2.7/site-packages/flask/__pycache__/_compat.cpython-35.pyc",
        "lib/python2.7/site-packages/flask/__pycache__/app.cpython-35.pyc",
        "lib/python2.7/site-packages/flask/__pycache__/blueprints.cpython-35.pyc",
        "lib/python2.7/site-packages/flask/__pycache__/cli.cpython-35.pyc",
        "lib/python2.7/site-packages/flask/__pycache__/config.cpython-35.pyc",
        "lib/python2.7/site-packages/flask/__pycache__/ctx.cpython-35.pyc",
        "lib/python2.7/site-packages/flask/__pycache__/debughelpers.cpython-35.pyc",
        "lib/python2.7/site-packages/flask/ext/__pycache__/__init__.cpython-35.pyc",
    )


def test_get_major_minor_version_no_dot():
    assert get_major_minor_version("3.5.2") == "3.5"
    assert get_major_minor_version("27") == "2.7"
    assert get_major_minor_version("bin/python2.7") == "2.7"
    assert get_major_minor_version("lib/python34/site-packages/") == "3.4"
    assert get_major_minor_version("python3") is None

    assert get_major_minor_version("3.10.0") == "3.10"
    assert get_major_minor_version("310") == "3.10"
    assert get_major_minor_version("bin/python3.10") == "3.10"
    assert get_major_minor_version("lib/python310/site-packages/") == "3.10"
    assert get_major_minor_version("python3") is None

    assert get_major_minor_version("3.5.2", False) == "35"
    assert get_major_minor_version("27", False) == "27"
    assert get_major_minor_version("bin/python2.7", False) == "27"
    assert get_major_minor_version("lib/python34/site-packages/", False) == "34"
    assert get_major_minor_version("python3", False) is None

    assert get_major_minor_version("3.10.0", False) == "310"
    assert get_major_minor_version("310", False) == "310"
    assert get_major_minor_version("bin/python3.10", False) == "310"
    assert get_major_minor_version("lib/python310/site-packages/", False) == "310"
    assert get_major_minor_version("python3", False) is None
