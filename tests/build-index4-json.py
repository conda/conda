import json
import requests


def main():
    r1 = requests.get('https://repo.anaconda.com/pkgs/main/linux-64/repodata.json')
    r1.raise_for_status()

    r1json = r1.json()

    packages = {}
    packages.update(r1json['packages'])

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

        'intel-openmp',
        'libgcc-ng',
        'libedit',
        'urllib3',
        'backports.shutil_get_terminal_size',
        'libgfortran-ng',
        'ncurses',
        'matplotlib',
        'ca-certificates',
        'chardet',
        'dask-core',
        'libstdcxx-ng',
        'backports.functools_lru_cache',
        'cycler',
        'freetype',
        'icu',
        'subprocess32',
        'pysocks',
        'pyqt',
        'libpng',
        'functools32',
        'qt',
        'sip',
        'dbus',
        'jpeg',
        'glib',
        'gst-plugins-base',
        'libxcb',
        'fontconfig',
        'expat',
        'pcre',
        'gstreamer',
        'libxml2',

        'parso',
        'openblas-devel',
        'libopenblas',

        'conda-build',
        'pkginfo',
        'glob2',
        'filelock',
        'conda-verify',
        'contextlib2',
        'patchelf',
        'beautifulsoup4',

        'conda',
        'cytoolz',

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


    additional_records = {
        "python-3.6.2-hda45abc_19.tar.bz2": {  # later hash, earlier timestamp
            "build": "hda45abc_19",
            "build_number": 19,
            "depends": [
                "libffi 3.2.*",
                "libgcc-ng >=7.2.0",
                "libstdcxx-ng >=7.2.0",
                "ncurses 6.0.*",
                "openssl 1.0.*",
                "readline 7.*",
                "sqlite >=3.20.1,<4.0a0",
                "tk 8.6.*",
                "xz >=5.2.3,<6.0a0",
                "zlib >=1.2.11,<1.3.0a0"
            ],
            "license": "PSF",
            "md5": "bdc6db1adbe7268e3ecbae13ec02066a",
            "name": "python",
            "sha256": "0b77f7c1f88f9b9dff2d25ab2c65b76ea37eb2fbc3eeab59e74a47b7a61ab20a",
            "size": 28300090,
            "subdir": "linux-64",
            "timestamp": 1507190714033,
            "version": "3.6.2"
        },
        "sqlite-3.20.1-haaaaaaa_4.tar.bz2": {  # deep cyclical dependency
            "build": "haaaaaaa_4",
            "build_number": 4,
            "depends": [
                "libedit",
                "libgcc-ng >=7.2.0",
                "jinja2 2.9.6"
            ],
            "license": "Public-Domain (http://www.sqlite.org/copyright.html)",
            "md5": "deadbeefdd677bc3ed98ddd4deadbeef",
            "name": "sqlite",
            "sha256": "deadbeefabd915d2f13da177a29e264e59a0ae3c6fd2a31267dcc6a8deadbeef",
            "size": 1540584,
            "subdir": "linux-64",
            "timestamp": 1505666646842,
            "version": "3.20.1"
        },
    }

    keep.update(additional_records)

    with open('index4.json', 'w') as fh:
        fh.write(json.dumps(keep, indent=2, sort_keys=True, separators=(',', ': ')))


if __name__ == "__main__":
    main()
