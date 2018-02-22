import json
import requests


def main():
    r1 = requests.get('https://repo.anaconda.com/pkgs/free/linux-64/repodata.json')
    r1.raise_for_status()
    r2 = requests.get('https://conda.anaconda.org/conda-test/noarch/repodata.json')
    r2.raise_for_status()
    r3 = requests.get('https://conda.anaconda.org/conda-test/linux-64/repodata.json')
    r3.raise_for_status()

    r1json = r1.json()
    r2json = r2.json()
    r3json = r3.json()

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
    )

    # keep = {}
    # missing_in_whitelist = set()
    #
    # for fn, info in packages.items():
    #     if info['name'] in keep_list:
    #         keep[fn] = info
    #         for dep in info['depends']:
    #             dep = dep.split()[0]
    #             if dep not in keep_list:
    #                 missing_in_whitelist.add(dep)
    #
    # if missing_in_whitelist:
    #     print(">>> missing <<<")
    #     print(missing_in_whitelist)
    #
    # with open('index2.json', 'w') as fh:
    #     fh.write(json.dumps(keep, indent=2, sort_keys=True, separators=(',', ': ')))



    keep_list = (
        'needs-spiffy-test-app',
        'openssl',
        'python',
        'readline',
        'spiffy-test-app',
        'sqlite',
        'system',
        'tk',
        'uses-spiffy-test-app',
        'xz',
        'zlib',
    )


    keep = {}
    # packages = r2json['packages'].copy()
    # packages.update(r3json['packages'])
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


    with open('index3.json', 'w') as fh:
        fh.write(json.dumps(keep, indent=2, sort_keys=True, separators=(',', ': ')))


if __name__ == "__main__":
    main()
