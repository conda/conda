"""
Tools for converting PyPI packages to conda recipes.
"""

# Don't put print_function here, it breaks the running of setup.py for
# packages that don't use it.
from __future__ import division, absolute_import

import sys
from os import makedirs, listdir, getcwd, chdir
from os.path import join, isdir, exists, isfile
from tempfile import mkdtemp
from collections import defaultdict
import keyword
import re

if sys.version_info < (3,):
    from xmlrpclib import ServerProxy
else:
    from xmlrpc.client import ServerProxy

from conda.fetch import download
from conda.utils import human_bytes, hashsum_file
from conda.install import rm_rf
from conda.builder.utils import tar_xf, unzip
from conda.builder.source import SRC_CACHE
from conda.compat import input, configparser, StringIO

PYPI_META = """\
package:
  name: {packagename}
  version: !!str {version}

source:
  fn: {filename}
  url: {pypiurl}
  {usemd5}md5: {md5}
#  patches:
   # List any patch files here
   # - fix.patch

{build_comment}build:
  {egg_comment}preserve_egg_dir: True
  {entry_comment}entry_points:
    # Put any entry points (scripts to be generated automatically) here. The
    # syntax is module:function.  For example
    #
    # - {packagename} = {packagename}:main
    #
    # Would create an entry point called {packagename} that calls {packagename}.main()
{entry_points}

  # If this is a new build for the same version, increment the build
  # number. If you do not include this key, it defaults to 0.
  # number: 1

requirements:
  build:
    - python{build_depends}

  run:
    - python{run_depends}

test:
  # Python imports
  {import_comment}imports:{import_tests}

  {entry_comment}commands:
    # You can put test commands to be run here.  Use this to test that the
    # entry points work.
{test_commands}

  # You can also put a file called run_test.py in the recipe that will be run
  # at test time.

  # requires:
    # Put any additional test requirements here.  For example
    # - nose

about:
  home: {homeurl}
  license: {license}

# See
# http://docs.continuum.io/conda/build.html for
# more information about meta.yaml
"""

PYPI_BUILD_SH = """\
#!/bin/bash

$PYTHON setup.py install

# Add more build steps here, if they are necessary.

# See
# http://docs.continuum.io/conda/build.html
# for a list of environment variables that are set during the build process.
"""

PYPI_BLD_BAT = """\
"%PYTHON%" setup.py install
if errorlevel 1 exit 1

:: Add more build steps here, if they are necessary.

:: See
:: http://docs.continuum.io/conda/build.html
:: for a list of environment variables that are set during the build process.
"""

def main(args, parser):
    client = ServerProxy(args.pypi_url)
    package_dicts = {}
    [output_dir] = args.output_dir
    indent = '\n    - '

    if len(args.packages) > 1 and args.download:
        # Because if a package's setup.py imports setuptools, it will make all
        # future packages look like they depend on distribute. Also, who knows
        # what kind of monkeypatching the setup.pys out there could be doing.
        print("WARNING: building more than one recipe at once without "
            "--no-download is not recommended")
    for package in args.packages:
        dir_path = join(output_dir, package.lower())
        if exists(dir_path):
            raise RuntimeError("directory already exists: %s" % dir_path)
        d = package_dicts.setdefault(package, {'packagename':
            package.lower(), 'run_depends':'',
            'build_depends':'', 'entry_points':'', 'build_comment':'# ',
            'test_commands':'', 'usemd5':'', 'entry_comment':'#', 'egg_comment':'#'})
        d['import_tests'] = valid(package).lower()
        if d['import_tests'] == '':
            d['import_comment'] = '# '
        else:
            d['import_comment'] = ''
            d['import_tests'] = indent+d['import_tests']

        if args.version:
            [version] = args.version
            versions = client.package_releases(package, True)
            if version not in versions:
                sys.exit("Error: Version %s of %s is not available on PyPI."
                    % (version, package))
            d['version'] = version
        else:
            versions = client.package_releases(package)
            if not versions:
                sys.exit("Error: Could not find any versions of package %s" % package)
            if len(versions) > 1:
                print("Warning, the following versions were found for %s" % package)
                for ver in versions:
                    print(ver)
                print("Using %s" % versions[0])
                print("Use --version to specify a different version.")
            d['version'] = versions[0]

        data = client.release_data(package, d['version'])
        urls = client.release_urls(package, d['version'])
        if not args.all_urls:
            # Try to find source urls
            urls = [url for url in urls if url['python_version'] == 'source']
        if not urls:
            if 'download_url' in data:
                urls = [defaultdict(str, {'url': data['download_url']})]
                urls[0]['filename'] = urls[0]['url'].split('/')[-1]
                d['usemd5'] = '#'
            else:
                sys.exit("Error: No source urls found for %s" % package)
        if len(urls) > 1 and not args.noprompt:
            print("More than one source version is available for %s:" % package)
            for i, url in enumerate(urls):
                print("%d: %s (%s) %s" % (i, url['url'],
                    human_bytes(url['size']), url['comment_text']))
            n = int(input("Which version should I use? "))
        else:
            n = 0

        print("Using url %s (%s) for %s." % (urls[n]['url'], urls[n]['size'], package))

        d['pypiurl'] = urls[n]['url']
        d['md5'] = urls[n]['md5_digest']
        d['filename'] = urls[n]['filename']


        d['homeurl'] = data['home_page']
        license_classifier = "License :: OSI Approved ::"
        licenses = [classifier.lstrip(license_classifier) for classifier in
            data['classifiers'] if classifier.startswith(license_classifier)]
        if not licenses:
            if data['license']:
                if args.noprompt:
                    license = data['license']
                else:
                    # Some projects put the whole license text in this field
                    print("This is the license for %s" % package)
                    print()
                    print(data['license'])
                    print()
                    license = input("What license string should I use? ")
            else:
                if args.noprompt:
                    license = "UNKNOWN"
                else:
                    license = input("No license could be found for %s on PyPI. What license should I use? " % package)
        else:
            license = ' or '.join(licenses)
        d['license'] = license

        # Unfortunately, two important pieces of metadata are only stored in
        # the package itself: the dependencies, and the entry points (if the
        # package uses distribute).  Our strategy is to download the package
        # and "fake" distribute/setuptools's setup() function to get this
        # information from setup.py. If this sounds evil, keep in mind that
        # distribute itself already works by monkeypatching distutils.
        if args.download:
            import yaml
            print("Downloading %s (use --no-download to skip this step)" % package)
            tempdir = mkdtemp('conda_skeleton')

            if not isdir(SRC_CACHE):
                makedirs(SRC_CACHE)

            try:
                # Download it to the build source cache. That way, you have
                # it.
                download_path = join(SRC_CACHE, d['filename'])
                if not isfile(download_path) or hashsum_file(download_path,
                                                             'md5') != d['md5']:
                    download(d['pypiurl'], join(SRC_CACHE, d['filename']))
                else:
                    print("Using cached download")
                print("Unpacking %s..." % package)
                unpack(join(SRC_CACHE, d['filename']), tempdir)
                print("done")
                print("working in %s" % tempdir)
                src_dir = get_dir(tempdir)
                # TODO: Do this in a subprocess. That way would be safer (the
                # setup.py can't mess up this code), it will allow building
                # multiple recipes without a setuptools import messing
                # everyone up, and it would prevent passing __future__ imports
                # through.
                patch_distutils(tempdir)
                run_setuppy(src_dir)
                with open(join(tempdir, 'pkginfo.yaml')) as fn:
                    pkginfo = yaml.load(fn)

                setuptools_build = 'setuptools' in sys.modules
                setuptools_run = False

                # Look at the entry_points and construct console_script and
                #  gui_scripts entry_points for conda and
                entry_points = pkginfo['entry_points']
                if entry_points:
                    if isinstance(entry_points, str):
                        # makes sure it is left-shifted
                        newstr = "\n".join(x.strip() for x in entry_points.split('\n'))
                        config = configparser.ConfigParser()
                        entry_points = {}
                        try:
                            config.readfp(StringIO(newstr))
                        except Exception as err:
                            print("WARNING: entry-points not understood: ", err)
                            print("The string was", newstr)
                            entry_points = pkginfo['entry_points']
                        else:
                            setuptools_run = True
                            for section in config.sections():
                                if section in ['console_scripts', 'gui_scripts']:
                                    value = ['%s=%s' % (option, config.get(section, option))
                                                 for option in config.options(section) ]
                                    entry_points[section] = value
                    if not isinstance(entry_points, dict):
                        print("WARNING: Could not add entry points. They were:")
                        print(entry_points)
                    else:
                        cs = entry_points.get('console_scripts', [])
                        gs = entry_points.get('gui_scripts',[])
                        # We have *other* kinds of entry-points so we need setuptools at run-time
                        if not cs and not gs and len(entry_points) > 1:
                            setuptools_build = True
                            setuptools_run = True
                        entry_list = (
                            cs
                            # TODO: Use pythonw for these
                            + gs)
                        if len(cs+gs) != 0:
                            d['entry_points'] = indent.join([''] + entry_list)
                            d['entry_comment'] = ''
                            d['build_comment'] = ''
                            d['test_commands'] = indent.join([''] + make_entry_tests(entry_list))


                if pkginfo['install_requires'] or setuptools_build or setuptools_run:
                    deps = [remove_version_information(dep).lower() for dep in
                        pkginfo['install_requires']]
                    if 'setuptools' in deps:
                        setuptools_build = False
                        setuptools_run = False
                        d['egg_comment'] = ''
                        d['build_comment'] = ''
                    d['build_depends'] = indent.join([''] +
                        ['setuptools']*setuptools_build + deps)
                    d['run_depends'] = indent.join([''] +
                        ['setuptools']*setuptools_run + deps)

                if pkginfo['packages']:
                    deps = set(pkginfo['packages'])
                    if d['import_tests']:
                        olddeps = [x for x in d['import_tests'].split() if x != '-']
                        deps = set(olddeps) | deps
                    d['import_tests'] = indent.join([''] + list(deps))
                    d['import_comment'] = ''
            finally:
                rm_rf(tempdir)


    for package in package_dicts:
        d = package_dicts[package]
        makedirs(join(output_dir, package.lower()))
        print("Writing recipe for %s" % package.lower())
        with open(join(output_dir, package.lower(), 'meta.yaml'),
            'w') as f:
            f.write(PYPI_META.format(**d))
        with open(join(output_dir, package.lower(), 'build.sh'), 'w') as f:
            f.write(PYPI_BUILD_SH.format(**d))
        with open(join(output_dir, package.lower(), 'bld.bat'), 'w') as f:
            f.write(PYPI_BLD_BAT.format(**d))

    print("Done")

def valid(name):
    if (re.match("[_A-Za-z][_a-zA-Z0-9]*$",name)
            and not keyword.iskeyword(name)):
        return name
    else:
        return ''

def unpack(src_path, tempdir):
    if src_path.endswith(('.tar.gz', '.tar.bz2', '.tgz', '.tar.xz', '.tar')):
        tar_xf(src_path, tempdir)
    elif src_path.endswith('.zip'):
        unzip(src_path, tempdir)
    else:
        raise Exception("not a valid source")

def get_dir(tempdir):
    lst = [fn for fn in listdir(tempdir) if not fn.startswith('.') and
        isdir(join(tempdir, fn))]
    if len(lst) == 1:
        dir_path = join(tempdir, lst[0])
        if isdir(dir_path):
            return dir_path
    raise Exception("could not find unpacked source dir")

def patch_distutils(tempdir):
    # Note, distribute doesn't actually patch the setup function.
    import distutils.core
    import yaml

    def setup(*args, **kwargs):
        data = {}
        data['install_requires'] = kwargs.get('install_requires', [])
        data['entry_points'] = kwargs.get('entry_points', [])
        data['packages'] = kwargs.get('packages', [])
        with open(join(tempdir, "pkginfo.yaml"), 'w') as fn:
            fn.write(yaml.dump(data))

    distutils.core.setup = setup

def run_setuppy(src_dir):
    import sys
    sys.argv = ['setup.py', 'install']
    sys.path.insert(0, src_dir)
    d = {'__file__': 'setup.py', '__name__': '__main__'}
    cwd = getcwd()
    chdir(src_dir)
    with open(join(src_dir, 'setup.py')) as f:
        exec(compile(f.read(), 'setup.py', 'exec'), d)
    chdir(cwd)

def remove_version_information(pkgstr):
    # TODO: Actually incorporate the version information into the meta.yaml
    # file.
    return pkgstr.partition(' ')[0].partition('<')[0].partition('!')[0].partition('>')[0].partition('=')[0]

def make_entry_tests(entry_list):
    tests = []
    for entry_point in entry_list:
        entry = entry_point.partition('=')[0].strip()
        tests.append(entry + " --help")
    return tests
