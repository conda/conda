"""
Tools for converting PyPI packages to conda recipes.
"""

from __future__ import print_function, division, absolute_import

import sys
import xmlrpclib
from os import makedirs
from os.path import join

from conda.utils import human_bytes

PYPI_META = """\
package:
  name: {packagename}
  version: {version}

source:
  fn: {filename}
  url: {pypiurl}
  md5: {md5}
#  patches:
   # List any patch files here
   # - fix.patch

# build:
  # entry_points:
    # Put any entry points (scripts to be generated automatically) here. The
    # syntax is module:function.  For example
    #
    # - {packagename}:main
    #
    # Would call {packagename}.main()

  # If this is a new build for the same version, increment the build
  # number. If you do not include this key, it defaults to 0.
  # number: 1

requirements:
  build:
    - python
    # If setuptools is required to run setup.py, add distribute to the build
    # requirements.
    #
    # - distribute

  run:
    - python

test:
  # Python imports
  imports:
    - {packagename}

  # commands:
    # You can put test commands to be run here.  Use this to test that the
    # entry points work.

  # You can also put a file called run_test.py in the recipe that will be run
  # at test time.

  # requires:
    # Put any test requirements here.  For example
    # - nose

about:
  home: {homeurl}
  license: {license}

# See
# https://github.com/ContinuumIO/conda/blob/master/conda/builder/README.txt for
# more information about meta.yaml
"""

PYPI_BUILD_SH = """\
#!/bin/bash

$PYTHON setup.py install

# Add more build steps here, if they are necessary.

# See
# https://github.com/ContinuumIO/conda/blob/master/conda/builder/README.txt
# for a list of environment variables that are set during the build process.
"""

PYPI_BLD_BAT = """\
"%PYTHON%" setup.py install
if errorlevel 1 exit 1

:: Add more build steps here, if they are necessary.

:: See
:: https://github.com/ContinuumIO/conda/blob/master/conda/builder/README.txt
:: for a list of environment variables that are set during the build process.
"""

def main(args, parser):
    client = xmlrpclib.ServerProxy(args.pypi_url)
    package_dicts = {}
    for package in args.packages:
        d = package_dicts.setdefault(package, {'packagename': package})
        if args.version:
            [version] = args.version
            versions = client.package_releases(package, True)
            if version not in versions:
                sys.exit("Error: Version %s of %s is not avalaiable on PyPI."
                    % (version, package))
            d['version'] = version
        else:
            versions = client.package_releases(package)
            if not versions:
                sys.exit("Error: Could not find any versions of package %s" % package)
            if len(versions) > 1:
                print "Warning, the following versions were found for %s" % package
                for ver in versions:
                    print ver
                print "Using %s" % versions[-1]
                print "Use --version to specify a different version."
            d['version'] = versions[-1]

        urls = client.release_urls(package, d['version'])
        if not args.all_urls:
            # Try to find source urls
            urls = [url for url in urls if url['python_version'] == 'source']
        if not urls:
            sys.exit("Error: No source urls found for %s" % package)
        if len(urls) > 1:
            print "More than one source version is available for %s:" % package
            for i, url in enumerate(urls):
                print "%d: %s (%s) %s" % (i, url['url'],
                    human_bytes(url['size']), url['comment_text'])
            n = int(raw_input("Which version should I use? "))
        else:
            n = 0

        print "Using url %s (%s) for %s." % (urls[n]['url'], urls[n]['size'], package)

        d['pypiurl'] = urls[n]['url']
        d['md5'] = urls[n]['md5_digest']
        d['filename'] = urls[n]['filename']

        data = client.release_data(package, d['version'])
        d['homeurl'] = data['home_page']
        license_classifier = "License :: OSI Approved ::"
        licenses = [classifier.lstrip(license_classifier) for classifier in
            data['classifiers'] if classifier.startswith(license_classifier)]
        if not licenses:
            if data['license']:
                # Some projects put the whole license text in this field
                print "This is the license for %s" % package
                print
                print data['license']
                print
                license = raw_input("What license string should I use? ")
            else:
                license = raw_input("No license could be found for %s on PyPI. What license should I use? " % package)
        else:
            license = ' or '.join(licenses)
        d['license'] = license

    for package in package_dicts:
        [output_dir] = args.output_dir
        d = package_dicts[package]
        makedirs(join(output_dir, package))
        print "Writing recipe for %s" % package
        with open(join(output_dir, package, 'meta.yaml'),
            'w') as f:
            f.write(PYPI_META.format(**d))
        with open(join(output_dir, package, 'build.sh'), 'w') as f:
            f.write(PYPI_BUILD_SH.format(**d))
        with open(join(output_dir, package, 'bld.bat'), 'w') as f:
            f.write(PYPI_BLD_BAT.format(**d))

    print "Done"
