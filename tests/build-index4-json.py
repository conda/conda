import json
from pprint import pprint

import requests

from conda.common.compat import itervalues


def main():
    keep = {}

    r0 = requests.get('https://repo.anaconda.com/pkgs/free/linux-64/repodata.json')
    r0.raise_for_status()
    r0json = r0.json()
    keep_list = (
        'gcc',
        'ipython-notebook',
    )
    _keep = {}
    missing_in_whitelist = set()
    for fn, info in r0json['packages'].items():
        if info['name'] in keep_list:
            _keep[fn] = info
            for dep in info['depends']:
                dep = dep.split()[0]
                if dep not in keep_list:
                    missing_in_whitelist.add(dep)
    # if missing_in_whitelist:
    #     print(">>> missing 0 (for info only; missing ok) <<<")
    #     pprint(missing_in_whitelist)
    keep.update(_keep)


    r1 = requests.get('https://repo.anaconda.com/pkgs/main/linux-64/repodata.json')
    r1.raise_for_status()
    r1json = r1.json()
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

        'mkl_fft',
        'mkl_random',
        'kiwisolver',
        'numpydoc',
        'blas',
        'libuuid',
        'numpy-base',
        'backcall',
        'sphinx',
        'alabaster',
        'sphinxcontrib-websupport',
        'imagesize',
        'typing',
        'babel',
        'snowballstemmer',
        'sphinxcontrib',

        'rpy2',

        'notebook',
        'ipykernel',
        'jupyter_client',
        'jupyter_core',
        'nbconvert',
        'nbformat',
        'send2trash',
        'terminado',
        'bleach',
        'entrypoints',
        'jsonschema',
        'mistune',
        'pandoc',
        'pandocfilters',
        'testpath',
        'html5lib',
        'configparser',

        'bwidget',
        'bzip2',
        'cairo',
        'configparser',
        'curl',
        'gcc_linux-64',
        'gfortran_linux-64',
        'gsl',
        'gxx_linux-64',
        'html5lib',
        'krb5',
        'libcurl',
        'libssh2',
        'libtiff',
        'pango',
        'tktable',
        'binutils_linux-64',
        'fribidi',
        'gcc_impl_linux-64',
        'gfortran_impl_linux-64',
        'graphite2',
        'gxx_impl_linux-64',
        'harfbuzz',
        'pixman',
        'webencodings',
        'binutils_impl_linux-64',
        'freeglut',
        'ipython-notebook',
        'jupyter',
        'libxslt',
        'qtconsole',
        'ipywidgets',
        'jupyter_console',
        'widgetsnbextension',

        'graphviz',
        'perl',
        'libtool',

        'python-graphviz',

    )
    _keep = {}
    missing_in_whitelist = set()
    for fn, info in r1json['packages'].items():
        if info['name'] in keep_list:
            _keep[fn] = info
            for dep in info['depends']:
                dep = dep.split()[0]
                if dep not in keep_list:
                    missing_in_whitelist.add(dep)
    if missing_in_whitelist:
        print(">>> missing 1 <<<")
        pprint(missing_in_whitelist)
    keep.update(_keep)


    r2 = requests.get('https://conda.anaconda.org/conda-test/noarch/repodata.json')
    r2.raise_for_status()
    r2json = r2.json()
    keep.update(r2json['packages'])

    r3 = requests.get('https://repo.continuum.io/pkgs/main/noarch/repodata.json')
    r3.raise_for_status()
    r3json = r3.json()
    keep.update(r3json['packages'])

    r4 = requests.get('https://repo.continuum.io/pkgs/r/linux-64/repodata.json')
    r4.raise_for_status()
    r4json = r4.json()
    _keep = {}
    missing_in_whitelist = set()
    keep_list = (
        'mro-base',
        'r-base',
        '_r-mutex',

        'nlopt',  # ignore this one

        'r-essentials',
        'r',
        'r-broom',
        'r-caret',
        'r-data.table',
        'r-dbi',
        'r-dplyr',
        'r-forcats',
        'r-formatr',
        'r-ggplot2',
        'r-glmnet',
        'r-haven',
        'r-hms',
        'r-httr',
        'r-irkernel',
        'r-jsonlite',
        'r-lubridate',
        'r-magrittr',
        'r-modelr',
        'r-plyr',
        'r-purrr',
        'r-quantmod',
        'r-randomforest',
        'r-rbokeh',
        'r-readr',
        'r-readxl',
        'r-recommended',
        'r-reshape2',
        'r-rmarkdown',
        'r-rvest',
        'r-shiny',
        'r-stringr',
        'r-tibble',
        'r-tidyr',
        'r-tidyverse',
        'r-xml2',
        'r-zoo',

        'mro-basics',
        'r-assertthat',
        'r-base64enc',
        'r-bh',
        'r-bindrcpp',
        'r-boot',
        'r-bradleyterry2',
        'r-car',
        'r-catools',
        'r-cellranger',
        'r-chron',
        'r-class',
        'r-cli',
        'r-cluster',
        'r-codetools',
        'r-crayon',
        'r-curl',
        'r-dbplyr',
        'r-digest',
        'r-evaluate',
        'r-foreach',
        'r-foreign',
        'r-gistr',
        'r-glue',
        'r-gtable',
        'r-hexbin',
        'r-htmltools',
        'r-htmlwidgets',
        'r-httpuv',
        'r-irdisplay',
        'r-kernsmooth',
        'r-knitr',
        'r-lattice',
        'r-lazyeval',
        'r-maps',
        'r-mass',
        'r-matrix',
        'r-memoise',
        'r-mgcv',
        'r-mime',
        'r-modelmetrics',
        'r-nlme',
        'r-nnet',
        'r-openssl',
        'r-pbdzmq',
        'r-pillar',
        'r-pkgconfig',
        'r-plogr',
        'r-proto',
        'r-pryr',
        'r-psych',
        'r-r6',
        'r-rcpp',
        'r-recipes',
        'r-repr',
        'r-reprex',
        'r-rjsonio',
        'r-rlang',
        'r-rpart',
        'r-rprojroot',
        'r-rstudioapi',
        'r-rzmq',
        'r-scales',
        'r-selectr',
        'r-sourcetools',
        'r-spatial',
        'r-stringi',
        'r-survival',
        'r-tidyselect',
        'r-ttr',
        'r-uuid',
        'r-withr',
        'r-xtable',
        'r-xts',
        'r-yaml',

        'r-backports',
        'r-bindr',
        'r-bitops',
        'r-brglm',
        'r-callr',
        'r-checkpoint',
        'r-clipr',
        'r-ddalpha',
        'r-deployrrserve',
        'r-dichromat',
        'r-dimred',
        'r-doparallel',
        'r-gower',
        'r-gtools',
        'r-highr',
        'r-ipred',
        'r-iterators',
        'r-labeling',
        'r-lme4',
        'r-markdown',
        'r-microsoftr',
        'r-mnormt',
        'r-munsell',
        'r-pbkrtest',
        'r-png',
        'r-quantreg',
        'r-qvcalc',
        'r-rcolorbrewer',
        'r-rcpproll',
        'r-rematch',
        'r-revoioq',
        'r-revomods',
        'r-revoutilsmath',
        'r-runit',
        'r-timedate',
        'r-utf8',
        'r-viridislite',
        'r-whisker',
        'r-colorspace',
        'r-drr',
        'r-matrixmodels',
        'r-minqa',
        'r-nloptr',
        'r-prodlim',
        'r-profilemodel',
        'r-rcppeigen',
        'r-robustbase',
        'r-sfsmisc',
        'r-sparsem',
        'r-lava',
        'r-deoptimr',
        'r-kernlab',
        'r-cvst',
        'r-numderiv',

    )
    all_package_names = set(info['name'] for info in itervalues(keep))
    for fn, info in r4json['packages'].items():
        if info['name'] in keep_list:
            _keep[fn] = info
            for dep in info['depends']:
                dep = dep.split()[0]
                if dep not in keep_list and dep not in all_package_names:
                    missing_in_whitelist.add(dep)
    if missing_in_whitelist:
        print(">>> missing 4 <<<")
        pprint(missing_in_whitelist)
    keep.update(_keep)



    r5 = requests.get('https://conda.anaconda.org/bioconda/linux-64/repodata.json')
    r5.raise_for_status()
    r5json = r5.json()
    _keep = {}
    missing_in_whitelist = set()
    keep_list = (
        'perl-graphviz',
        'perl-file-which',
        'perl-ipc-run',
        'perl-libwww-perl',
        'perl-parse-recdescent',
        'perl-test-pod',
        'perl-threaded',
        'perl-xml-twig',
        'perl-xml-xpath',
        'perl-app-cpanminus',
        'perl-encode-locale',
        'perl-file-listing',
        'perl-html-entities-numbered',
        'perl-html-formatter',
        'perl-html-parser',
        'perl-html-tidy',
        'perl-html-tree',
        'perl-http-cookies',
        'perl-http-daemon',
        'perl-http-date',
        'perl-http-message',
        'perl-http-negotiate',
        'perl-io-tty',
        'perl-lwp-mediatypes',
        'perl-net-http',
        'perl-ntlm',
        'perl-tie-ixhash',
        'perl-uri',
        'perl-www-robotrules',
        'perl-xml-parser',
        'perl-xml-xpathengine',
        'perl-digest-hmac',
        'perl-font-afm',
        'perl-html-tagset',
        'perl-io-html',
        'perl-io-socket-ssl',
        'perl-scalar-list-utils',
        'tidyp',
        'perl-net-ssleay',
        'perl-mime-base64',
        'perl-xsloader',
        'perl-test-more',
    )
    all_package_names = set(info['name'] for info in itervalues(keep))
    for fn, info in r5json['packages'].items():
        if info['name'] in keep_list:
            _keep[fn] = info
            for dep in info['depends']:
                dep = dep.split()[0]
                if dep not in keep_list and dep not in all_package_names:
                    missing_in_whitelist.add(dep)
    if missing_in_whitelist:
        print(">>> missing 5 <<<")
        pprint(missing_in_whitelist)
    keep.update(_keep)



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


    all_package_names = set(info['name'] for info in itervalues(keep))
    ignore_names = {
        'nlopt',
    }
    missing = set()
    for info in itervalues(keep):
        for line in info['depends']:
            package_name = line.split(' ')[0]
            if package_name not in all_package_names and package_name not in ignore_names:
                missing.add(package_name)
    if missing:
        print(">>> missing final <<<")
        pprint(missing)


    with open('index4.json', 'w') as fh:
        fh.write(json.dumps(keep, indent=2, sort_keys=True, separators=(',', ': ')))


if __name__ == "__main__":
    main()
