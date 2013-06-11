"""
Tools for converting PyPI packages to conda recipes.
"""

import sys
import xmlrpclib

from conda.cli.conda_argparse import ArgumentParser
from conda.utils import human_bytes

PYPI_META = """
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
  imports:
    - {packagename}

  # You can also put a file called run_test.py in the recipe that will be run
  # at test time.

about:
  home: {homeurl}
  license: {license}
"""

PYPI_BUILD_SH = """
#!/bin/bash

$PYTHON setup.py install

# Add more build steps here, if they are necessary.
"""

PYPI_BLD_BAT = """
python setup.py install
if errorlevel 1 exit 1

# Add more build steps here, if they are necessary.
"""

def main():
    p = ArgumentParser(
        description='A tool for building recipes from PyPI packages',
        )
    p.add_argument(
        "packages",
        action = "store",
        nargs = '+',
        help = "PyPi packages to create recipe skeletons for",
        )
    args = p.parse_args()
    execute(args, p)

def execute(args, parser):
    client = xmlrpclib.ServerProxy('http://pypi.python.org/pypi')
    for package in args.packages:
        d = {'packagename': package}
        versions = client.package_releases(package)
        if not versions:
            sys.exit("Error: Could not find any versions of package %s" % package)
        if len(versions) > 1:
            print "Warning, the following versions were found for %s" % package
            for ver in versions:
                print ver
            print "Using %s" % versions[-1]
            # TODO: Allow to specify the version
        d['version'] = versions[-1]

        urls = client.release_urls(package, d['version'])
        # Try to find source urls
        # TODO: Allow to customize this
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

        d['pypiurl'] = urls[n]['url']
        d['md5'] = urls[n]['md5_digest']
        d['filename'] = urls[n]['filename']

        data = client.release_data(package, d['version'])
        d['homepage'] = data['home_page']
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

if __name__ == '__main__':
    sys.exit(main())
