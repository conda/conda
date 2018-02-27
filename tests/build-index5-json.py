import json
import requests


def main():
    r1 = requests.get('https://repo.anaconda.com/pkgs/main/win-64/repodata.json')
    r1.raise_for_status()

    r1json = r1.json()

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


    r2 = requests.get('https://conda.anaconda.org/conda-test/noarch/repodata.json')
    r2.raise_for_status()
    r2json = r2.json()
    keep.update(r2json['packages'])

    r3 = requests.get('https://repo.continuum.io/pkgs/main/noarch/repodata.json')
    r3.raise_for_status()
    r3json = r3.json()
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

    with open('index5.json', 'w') as fh:
        fh.write(json.dumps(keep, indent=2, sort_keys=True, separators=(',', ': ')))


if __name__ == "__main__":
    main()
