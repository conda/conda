# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import json
from os.path import abspath, dirname, join

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
    r1json = read_data_source("free_linux-64")
    r2json = read_data_source("conda-test_noarch")
    r3json = read_data_source("conda-test_linux-64")

    packages = r3json['packages'].copy()
    packages.update(r1json['packages'])
    packages.update(r2json['packages'])



    keep_list = (
        'asn1crypto',
        'astroid',
        'backports',
        'backports_abc',
        'bkcharts',
        'bokeh',
        'boto3',
        'botocore',
        'certifi',
        'cffi',
        'chest',
        'click',
        'cloog',
        'cloudpickle',
        'colorama',
        'conda',
        'conda-env',
        'cryptography',
        'dask',
        'dateutil',
        'decorator',
        'dill',
        'distribute',
        'distributed',
        'docutils',
        'enum34',
        'flask',
        'funcsigs',
        'futures',
        'get_terminal_size',
        'gevent',
        'gevent-websocket',
        'gmp',
        'greenlet',
        'heapdict',
        'idna',
        'ipaddress',
        'ipython',
        'ipython_genutils',
        'isl',
        'itsdangerous',
        'jedi',
        'jinja2',
        'jmespath',
        'lazy-object-proxy',
        'libevent',
        'libffi',
        'libgcc',
        'libgfortran',
        'libsodium',
        'llvm',
        'llvmlite',
        'llvmmath',
        'llvmpy',
        'locket',
        'logilab-common',
        'lz4',
        'markupsafe',
        'meta',
        'mkl',
        'mpc',
        'mpfr',
        'msgpack-python',
        'needs-spiffy-test-app',
        'nomkl',
        'nose',
        'numpy',
        'openblas',
        'openssl',
        'ordereddict',
        'packaging',
        'pandas',
        'partd',
        'path.py',
        'pathlib2',
        'pexpect',
        'pickleshare',
        'pip',
        'prompt_toolkit',
        'psutil',
        'ptyprocess',
        'pyasn1',
        'pycosat',
        'pycparser',
        'pygments',
        'pyopenssl',
        'pyparsing',
        'python',
        'python-dateutil',
        'pytz',
        'pyyaml',
        'pyzmq',
        'readline',
        'redis',
        'redis-py',
        'requests',
        'ruamel_yaml',
        's3fs',
        's3transfer',
        'scandir',
        'scipy',
        'setuptools',
        'simplegeneric',
        'singledispatch',
        'six',
        'sortedcollections',
        'sortedcontainers',
        'spiffy-test-app',
        'sqlite',
        'ssl_match_hostname',
        'system',
        'tblib',
        'tk',
        'toolz',
        'tornado',
        'traitlets',
        'ujson',
        'uses-spiffy-test-app',
        'util-linux',
        'wcwidth',
        'werkzeug',
        'wheel',
        'wrapt',
        'xz',
        'yaml',
        'zeromq',
        'zict',
        'zlib',

        'system',
        'functools_lru_cache',
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
        print(missing_in_whitelist)

    with open(join(dirname(__file__), 'index2.json'), 'w') as fh:
        fh.write(json.dumps(keep, indent=2, sort_keys=True, separators=(',', ': ')))


if __name__ == "__main__":
    save_data_source("https://conda-static.anaconda.org/free/linux-64", "free_linux-64")
    # save_data_source("https://conda.anaconda.org/conda-test/noarch", "conda-test_noarch")
    # save_data_source("https://conda.anaconda.org/conda-test/linux-64", "conda-test_linux-64")
    main()
