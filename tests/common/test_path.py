# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from conda.common.path import missing_pyc_files, get_major_minor_version
from logging import getLogger

log = getLogger(__name__)


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

    assert get_major_minor_version("3.5.2", False) == "35"
    assert get_major_minor_version("27", False) == "27"
    assert get_major_minor_version("bin/python2.7", False) == "27"
    assert get_major_minor_version("lib/python34/site-packages/", False) == "34"
    assert get_major_minor_version("python3", False) is None
