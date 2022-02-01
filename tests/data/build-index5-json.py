# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import json
from os.path import abspath, dirname, join
from pprint import pprint

from conda.core.subdir_data import fetch_repodata_remote_request

DATA_DIR = abspath(join(dirname(__file__), "repodata"))

def save_data_source(url, name):
    raw_repodata_str = fetch_repodata_remote_request(url, None, None)
    json.loads(raw_repodata_str)
    with open(join(DATA_DIR, name + ".json"), 'w') as fh:
        json.dump(json.loads(raw_repodata_str), fh, indent=2, sort_keys=True, separators=(',', ': '))


def read_data_source(name):
    with open(join(DATA_DIR, name + ".json")) as fh:
        return json.load(fh)


def main():
    r1json = read_data_source("main_win-64")

    packages = {}
    packages.update(r1json['packages'])

    keep_list = (

        'python',
        'vs2008_runtime',
        'vs2015_runtime',
        'vc',

        'requests',
        'urllib3',
        'idna',
        'chardet',
        'certifi',
        'pyopenssl',
        'cryptography',
        'ipaddress',
        'pysocks',
        'win_inet_pton',
        'openssl',
        'cffi',
        'enum34',
        'six',
        'asn1crypto',
        'pycparser',
        'ca-certificates',

        'pip',
        'colorama',
        'progress',
        'html5lib',
        'wheel',
        'distlib',
        'packaging',
        'lockfile',
        'webencodings',
        'cachecontrol',
        'pyparsing',
        'msgpack-python',

        'conda',
        'menuinst',
        'futures',
        'ruamel_yaml',
        'pycosat',
        'conda-env',
        'yaml',
        'pywin32',
        'cytoolz',
        'toolz',

        'conda-build',
        'pyyaml',
        'jinja2',
        'pkginfo',
        'contextlib2',
        'beautifulsoup4',
        'conda-verify',
        'filelock',
        'glob2',
        'psutil',
        'scandir',
        'setuptools',
        'markupsafe',
        'wincertstore',

        'click',
        'future',
        'backports.functools_lru_cache',
        'cryptography-vectors',
        'backports',

        'colour',
        'affine',

    )

    keep = {}
    missing_in_whitelist = set()

    for fn, info in packages.items():
        if info['name'] in keep_list:
            keep[fn] = info
            for dep in info['depends']:
                dep = dep.split()[0]
                if dep not in keep_list:
                    missing_in_whitelist.add(dep)

    if missing_in_whitelist:
        print(">>> missing <<<")
        pprint(missing_in_whitelist)

    r2json = read_data_source("conda-test_noarch")
    keep.update(r2json['packages'])

    r3json = read_data_source("main_noarch")
    keep.update(r3json['packages'])

    # additional_records = {
    #     "python-3.6.2-hda45abc_19.tar.bz2": {  # later hash, earlier timestamp
    #         "build": "hda45abc_19",
    #         "build_number": 19,
    #         "depends": [
    #             "libffi 3.2.*",
    #             "libgcc-ng >=7.2.0",
    #             "libstdcxx-ng >=7.2.0",
    #             "ncurses 6.0.*",
    #             "openssl 1.0.*",
    #             "readline 7.*",
    #             "sqlite >=3.20.1,<4.0a0",
    #             "tk 8.6.*",
    #             "xz >=5.2.3,<6.0a0",
    #             "zlib >=1.2.11,<1.3.0a0"
    #         ],
    #         "license": "PSF",
    #         "md5": "bdc6db1adbe7268e3ecbae13ec02066a",
    #         "name": "python",
    #         "sha256": "0b77f7c1f88f9b9dff2d25ab2c65b76ea37eb2fbc3eeab59e74a47b7a61ab20a",
    #         "size": 28300090,
    #         "subdir": "linux-64",
    #         "timestamp": 1507190714033,
    #         "version": "3.6.2"
    #     },
    # }
    #
    # keep.update(additional_records)

    with open(join(dirname(__file__), 'index5.json'), 'w') as fh:
        fh.write(json.dumps(keep, indent=2, sort_keys=True, separators=(',', ': ')))


if __name__ == "__main__":
    # save_data_source("https://conda-static.anaconda.org/main/win-64", "main_win-64")
    # save_data_source("https://conda.anaconda.org/conda-test/noarch", "conda-test_noarch")
    # save_data_source("https://conda-static.anaconda.org/main/noarch", "main_noarch")
    main()
