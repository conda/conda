Conda build framework
=====================

(these are just preliminary notes, nothing is implemented yet)

Building a package requires a recipe.  A recipe is flat directory which
contains to following files:
  * meta.yaml (metadata file)
  * build.sh (Unix build script which is executed using bash)
  * bld.bat  (Windows build script which is executed using cmd)
  * run_test.py (optional Python test file)
  * patches to the source (optional, see below)

When building a package, the following steps are invoked:
  * read the metadata
  * download the source (into a cache)
  * extract the source in a "source directory"
  * apply the patches
  * create a "build environment" (build dependencies are installed here)
  * run the actual build script:
      - cwd is the "source directory"
      - with environment variables set
      - in the build script installs into the "build environment"
  * do some necessary post processing steps: shebang, runpath, etc.
  * add conda metadata to the "build environment"
  * package up the new files in the "build environment" into a conda package
  * test the new conda package:
      - create a "test environment" with the package (and its dependencies)
      - run the test script


The meta.yaml file:
-------------------

package:
  name: bsdiff4     # lower case name of package, may contain '-' but no spaces
  version: 1.1.4    # version of package

source:
# The source section speficies where the source code of the package is comming
# from, it may be comming from a source tarball like:
  fn: qt-everywhere-opensource-src-4.8.4.tar.gz
  url: http://filer/src/qt-everywhere-opensource-src-4.8.4.tar.gz
  md5: 89c5ecba180cae74c66260ac732dc5cb              # (optional)
# or from git:
  git_url: git@github.com:ilanschnell/bsdiff4.git
  git_tag: 1.1.4                                     # (optional)
# also optionally patches may be applied to the source
  patches:
    - my.patch    # the patch file is expected to be found in the recipe

build:            # (optional)
  number: 1                          (optional, defaults to 0)
# optional Python entry points
  entry_points:
    - bsdiff4 = bsdiff4.cli:main_bsdiff4
    - bspatch4 = bsdiff4.cli:main_bspatch4

# the build and runtime requirements:
requirements:     # (optional)
  build:
    - python
  run:
    - python

test:             # (optional)
# commands we want to make sure they work, which are expected to get installed
# by the package
  commands:
    - bsdiff4 -h
    - bspatch4 -h
# Python imports
  imports:
    - bsdiff4

about:            # (optional)
  home: https://github.com/ilanschnell/bsdiff4
  license: BSD
