# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from pathlib import Path
from pprint import pprint

from conda.common.compat import on_win
from conda.common.path import get_python_site_packages_short_path
from conda.common.serialize import json
from conda.plugins.prefix_data_loaders.pypi.pkg_format import read_python_record

ENV_METADATA_DIR = Path(__file__).parent.parent.parent / "data" / "env_metadata"


def test_scrapy_py36_osx_whl():
    anchor_file = "lib/python3.6/site-packages/Scrapy-1.5.1.dist-info/RECORD"
    prefix_path = str(ENV_METADATA_DIR / "py36-osx-whl")
    prefix_rec = read_python_record(prefix_path, anchor_file, "3.6")

    dumped_rec = json.loads(json.dumps(prefix_rec.dump()))
    files = dumped_rec.pop("files")
    paths_data = dumped_rec.pop("paths_data")
    print(json.dumps(dumped_rec))
    assert dumped_rec == {
        "build": "pypi_0",
        "build_number": 0,
        "channel": "https://conda.anaconda.org/pypi",
        "constrains": [],
        "depends": [
            "cssselect >=0.9",
            "lxml",
            "parsel >=1.1",
            "pydispatcher >=2.0.5",
            "pyopenssl",
            "python 3.6.*",
            "queuelib",
            "service-identity",
            "six >=1.5.2",
            "twisted >=13.1.0",
            "w3lib >=1.17.0",
        ],
        "fn": "Scrapy-1.5.1.dist-info",
        "name": "scrapy",
        "package_type": "virtual_python_wheel",
        "subdir": "pypi",
        "version": "1.5.1",
    }
    print(json.dumps(files))
    print(json.dumps(paths_data["paths"]))
    sp_dir = get_python_site_packages_short_path("3.6")
    assert sp_dir + "/scrapy/core/scraper.py" in files
    assert sp_dir + "/scrapy/core/__pycache__/scraper.cpython-36.pyc" in files
    pd1 = {
        "_path": sp_dir + "/scrapy/core/scraper.py",
        "path_type": "hardlink",
        "sha256": "db9e7d5fd9f6cf560a74557d1253110faffcf0b21da87d5ad94c108a64adb769",
        "size_in_bytes": 9960,
    }
    assert pd1 in paths_data["paths"]
    pd2 = {
        "_path": sp_dir + "/scrapy/core/__pycache__/scraper.cpython-36.pyc",
        "path_type": "hardlink",
        "sha256": None,
        "size_in_bytes": None,
    }
    assert pd2 in paths_data["paths"]
    pd3 = {
        "_path": "../bin/scrapy" if on_win else "bin/scrapy",
        "path_type": "hardlink",
        "sha256": "467700028c521274a2ff4548a29691c6caba92bc9018beb561b13078dd935b78",
        "size_in_bytes": 268,
    }
    assert pd3 in paths_data["paths"]


def test_twilio_py36_osx_whl():
    anchor_file = "lib/python3.6/site-packages/twilio-6.16.1.dist-info/RECORD"
    prefix_path = str(ENV_METADATA_DIR / "py36-osx-whl")
    prefix_rec = read_python_record(prefix_path, anchor_file, "3.6")
    pprint(prefix_rec.depends)
    pprint(prefix_rec.constrains)

    dumped_rec = json.loads(json.dumps(prefix_rec.dump()))
    files = dumped_rec.pop("files")
    paths_data = dumped_rec.pop("paths_data")
    print(json.dumps(dumped_rec))
    assert dumped_rec == {
        "build": "pypi_0",
        "build_number": 0,
        "channel": "https://conda.anaconda.org/pypi",
        "constrains": [],
        "depends": [
            "pyjwt >=1.4.2",
            "pysocks",
            "python 3.6.*",
            "pytz",
            "requests >=2.0.0",
            "six",
        ],
        "fn": "twilio-6.16.1.dist-info",
        "name": "twilio",
        "package_type": "virtual_python_wheel",
        "subdir": "pypi",
        "version": "6.16.1",
    }
    print(json.dumps(files))
    print(json.dumps(paths_data["paths"]))
    sp_dir = get_python_site_packages_short_path("3.6")
    assert sp_dir + "/twilio/compat.py" in files
    assert sp_dir + "/twilio/__pycache__/compat.cpython-36.pyc" in files
    pd1 = {
        "_path": sp_dir + "/twilio/compat.py",
        "path_type": "hardlink",
        "sha256": "b09d6dec22afc698a9897e5cc87d58c174dfde7fc5b0b7ffb5a521b8256c0b01",
        "size_in_bytes": 517,
    }
    assert pd1 in paths_data["paths"]
    pd2 = {
        "_path": sp_dir + "/twilio/jwt/__pycache__/compat.cpython-36.pyc",
        "path_type": "hardlink",
        "sha256": None,
        "size_in_bytes": None,
    }
    assert pd2 in paths_data["paths"]


def test_pyjwt_py36_osx_whl():
    anchor_file = "lib/python3.6/site-packages/PyJWT-1.6.4.dist-info/RECORD"
    prefix_path = str(ENV_METADATA_DIR / "py36-osx-whl")
    prefix_rec = read_python_record(prefix_path, anchor_file, "3.6")

    dumped_rec = json.loads(json.dumps(prefix_rec.dump()))
    files = dumped_rec.pop("files")
    paths_data = dumped_rec.pop("paths_data")
    print(json.dumps(dumped_rec))
    assert dumped_rec == {
        "build": "pypi_0",
        "build_number": 0,
        "channel": "https://conda.anaconda.org/pypi",
        "constrains": ["cryptography >=1.4", "pytest <4,>3"],
        "depends": ["python 3.6.*"],
        "fn": "PyJWT-1.6.4.dist-info",
        "name": "pyjwt",
        "package_type": "virtual_python_wheel",
        "subdir": "pypi",
        "version": "1.6.4",
    }
    print(json.dumps(files))
    print(json.dumps(paths_data["paths"]))
    sp_dir = get_python_site_packages_short_path("3.6")
    assert ("../bin/pyjwt" if on_win else "bin/pyjwt") in files
    assert sp_dir + "/jwt/__pycache__/__init__.cpython-36.pyc" in files
    pd1 = {
        "_path": "../bin/pyjwt" if on_win else "bin/pyjwt",
        "path_type": "hardlink",
        "sha256": "c19113ff6e2e643129b0c761010efc02cb3693eefa690e7dc8f484e034c4d93a",
        "size_in_bytes": 260,
    }
    assert pd1 in paths_data["paths"]
    pd2 = {
        "_path": sp_dir + "/jwt/contrib/__pycache__/__init__.cpython-36.pyc",
        "path_type": "hardlink",
        "sha256": None,
        "size_in_bytes": None,
    }
    assert pd2 in paths_data["paths"]


def test_cherrypy_py36_osx_whl():
    anchor_file = "lib/python3.6/site-packages/CherryPy-17.2.0.dist-info/RECORD"
    prefix_path = str(ENV_METADATA_DIR / "py36-osx-whl")
    prefix_rec = read_python_record(prefix_path, anchor_file, "3.6")

    dumped_rec = json.loads(json.dumps(prefix_rec.dump()))
    dumped_rec.pop("files")
    dumped_rec.pop("paths_data")
    print(json.dumps(dumped_rec))
    constrains = dumped_rec.pop("constrains")
    depends = dumped_rec.pop("depends")
    assert dumped_rec == {
        "build": "pypi_0",
        "build_number": 0,
        "channel": "https://conda.anaconda.org/pypi",
        "fn": "CherryPy-17.2.0.dist-info",
        "name": "cherrypy",
        "package_type": "virtual_python_wheel",
        "subdir": "pypi",
        "version": "17.2.0",
    }

    assert constrains == [
        "jaraco-packaging >=3.2",
        # "pypiwin32 ==219",
        "pytest >=2.8",
        "python-memcached >=1.58",
        "routes >=2.3.1",
        "rst-linker >=1.9",
    ]
    if on_win:
        assert depends == [
            "cheroot >=6.2.4",
            "more-itertools",
            "portend >=2.1.1",
            "python 3.6.*",
            "pywin32",
            "six >=1.11.0",
        ]
    else:
        assert depends == [
            "cheroot >=6.2.4",
            "more-itertools",
            "portend >=2.1.1",
            "python 3.6.*",
            "six >=1.11.0",
        ]


def test_scrapy_py27_osx_no_binary():
    anchor_file = "lib/python2.7/site-packages/Scrapy-1.5.1-py2.7.egg-info/PKG-INFO"
    prefix_path = str(ENV_METADATA_DIR / "py27-osx-no-binary")
    prefix_rec = read_python_record(prefix_path, anchor_file, "2.7")

    dumped_rec = json.loads(json.dumps(prefix_rec.dump()))
    files = dumped_rec.pop("files")
    paths_data = dumped_rec.pop("paths_data")
    print(json.dumps(dumped_rec))
    assert dumped_rec == {
        "build": "pypi_0",
        "build_number": 0,
        "channel": "https://conda.anaconda.org/pypi",
        "constrains": [],
        "depends": [
            "cssselect >=0.9",
            "lxml",
            "parsel >=1.1",
            "pydispatcher >=2.0.5",
            "pyopenssl",
            "python 2.7.*",
            "queuelib",
            "service-identity",
            "six >=1.5.2",
            "twisted >=13.1.0",
            "w3lib >=1.17.0",
        ],
        "fn": "Scrapy-1.5.1-py2.7.egg-info",
        "name": "scrapy",
        "package_type": "virtual_python_egg_manageable",
        "subdir": "pypi",
        "version": "1.5.1",
    }
    print(json.dumps(files))
    print(json.dumps(paths_data["paths"]))
    sp_dir = get_python_site_packages_short_path("2.7")
    assert sp_dir + "/scrapy/contrib/downloadermiddleware/decompression.py" in files
    assert sp_dir + "/scrapy/downloadermiddlewares/decompression.pyc" in files
    assert ("../bin/scrapy" if on_win else "bin/scrapy") in files
    pd1 = {
        "_path": sp_dir + "/scrapy/contrib/downloadermiddleware/decompression.py",
        "path_type": "hardlink",
    }
    assert pd1 in paths_data["paths"]
    pd2 = {
        "_path": sp_dir + "/scrapy/contrib/downloadermiddleware/decompression.pyc",
        "path_type": "hardlink",
    }
    assert pd2 in paths_data["paths"]
    pd3 = {
        "_path": "../bin/scrapy" if on_win else "bin/scrapy",
        "path_type": "hardlink",
    }
    assert pd3 in paths_data["paths"]


def test_twilio_py27_osx_no_binary():
    anchor_file = "lib/python2.7/site-packages/twilio-6.16.1-py2.7.egg-info/PKG-INFO"
    prefix_path = str(ENV_METADATA_DIR / "py27-osx-no-binary")
    prefix_rec = read_python_record(prefix_path, anchor_file, "2.7")
    pprint(prefix_rec.depends)
    pprint(prefix_rec.constrains)

    dumped_rec = json.loads(json.dumps(prefix_rec.dump()))
    files = dumped_rec.pop("files")
    paths_data = dumped_rec.pop("paths_data")
    print(json.dumps(dumped_rec))
    assert dumped_rec == {
        "build": "pypi_0",
        "build_number": 0,
        "channel": "https://conda.anaconda.org/pypi",
        "constrains": [],
        "depends": ["pyjwt >=1.4.2", "python 2.7.*", "pytz", "requests >=2.0.0", "six"],
        "fn": "twilio-6.16.1-py2.7.egg-info",
        "name": "twilio",
        "package_type": "virtual_python_egg_manageable",
        "subdir": "pypi",
        "version": "6.16.1",
    }
    print(json.dumps(files))
    print(json.dumps(paths_data["paths"]))
    sp_dir = get_python_site_packages_short_path("2.7")
    assert sp_dir + "/twilio/compat.py" in files
    assert sp_dir + "/twilio/compat.pyc" in files
    pd1 = {"_path": sp_dir + "/twilio/compat.py", "path_type": "hardlink"}
    assert pd1 in paths_data["paths"]
    pd2 = {"_path": sp_dir + "/twilio/jwt/compat.pyc", "path_type": "hardlink"}
    assert pd2 in paths_data["paths"]


def test_pyjwt_py27_osx_no_binary():
    anchor_file = "lib/python2.7/site-packages/PyJWT-1.6.4-py2.7.egg-info/PKG-INFO"
    prefix_path = str(ENV_METADATA_DIR / "py27-osx-no-binary")
    prefix_rec = read_python_record(prefix_path, anchor_file, "2.7")

    dumped_rec = json.loads(json.dumps(prefix_rec.dump()))
    files = dumped_rec.pop("files")
    paths_data = dumped_rec.pop("paths_data")
    print(json.dumps(dumped_rec))
    assert dumped_rec == {
        "build": "pypi_0",
        "build_number": 0,
        "channel": "https://conda.anaconda.org/pypi",
        "constrains": ["cryptography >=1.4", "pytest <4,>3"],
        "depends": ["python 2.7.*"],
        "fn": "PyJWT-1.6.4-py2.7.egg-info",
        "name": "pyjwt",
        "package_type": "virtual_python_egg_manageable",
        "subdir": "pypi",
        "version": "1.6.4",
    }
    print(json.dumps(files))
    print(json.dumps(paths_data["paths"]))
    sp_dir = get_python_site_packages_short_path("2.7")
    assert ("../bin/pyjwt" if on_win else "bin/pyjwt") in files
    assert sp_dir + "/jwt/__init__.pyc" in files
    pd1 = {"_path": "../bin/pyjwt" if on_win else "bin/pyjwt", "path_type": "hardlink"}
    assert pd1 in paths_data["paths"]
    pd2 = {"_path": sp_dir + "/jwt/contrib/__init__.pyc", "path_type": "hardlink"}
    assert pd2 in paths_data["paths"]


def test_cherrypy_py27_osx_no_binary():
    anchor_file = "lib/python2.7/site-packages/CherryPy-17.2.0-py2.7.egg-info/PKG-INFO"
    prefix_path = str(ENV_METADATA_DIR / "py27-osx-no-binary")
    prefix_rec = read_python_record(prefix_path, anchor_file, "2.7")

    dumped_rec = json.loads(json.dumps(prefix_rec.dump()))
    dumped_rec.pop("files")
    dumped_rec.pop("paths_data")
    print(json.dumps(dumped_rec))
    constrains = dumped_rec.pop("constrains")
    depends = dumped_rec.pop("depends")
    assert dumped_rec == {
        "build": "pypi_0",
        "build_number": 0,
        "channel": "https://conda.anaconda.org/pypi",
        "fn": "CherryPy-17.2.0-py2.7.egg-info",
        "name": "cherrypy",
        "package_type": "virtual_python_egg_manageable",
        "subdir": "pypi",
        "version": "17.2.0",
    }
    assert constrains == [
        "jaraco-packaging >=3.2",
        "pytest >=2.8",
        "python-memcached >=1.58",
        "routes >=2.3.1",
        "rst-linker >=1.9",
    ]
    if on_win:
        assert depends == [
            "cheroot >=6.2.4",
            "more-itertools",
            "portend >=2.1.1",
            "python 2.7.*",
            "pywin32",
            "six >=1.11.0",
        ]
    else:
        assert depends == [
            "cheroot >=6.2.4",
            "more-itertools",
            "portend >=2.1.1",
            "python 2.7.*",
            "six >=1.11.0",
        ]


def test_six_py27_osx_no_binary_unmanageable():
    anchor_file = "lib/python2.7/site-packages/six-1.11.0-py2.7.egg-info/PKG-INFO"
    prefix_path = str(ENV_METADATA_DIR / "py27-osx-no-binary")
    prefix_rec = read_python_record(prefix_path, anchor_file, "2.7")

    dumped_rec = json.loads(json.dumps(prefix_rec.dump()))
    files = dumped_rec.pop("files")
    dumped_rec.pop("paths_data")
    print(json.dumps(dumped_rec))
    assert dumped_rec == {
        "build": "pypi_0",
        "build_number": 0,
        "channel": "https://conda.anaconda.org/pypi",
        "constrains": [],
        "depends": ["python 2.7.*"],
        "fn": "six-1.11.0-py2.7.egg-info",
        "name": "six",
        "package_type": "virtual_python_egg_unmanageable",
        "subdir": "pypi",
        "version": "1.11.0",
    }
    assert not files
    assert not prefix_rec.paths_data.paths
