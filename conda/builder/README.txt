Building a package requires a "recipe" in most cases.
A recipe contains:
  * metadata
  * patches to the source
  * build script (bash or bat file)
  * tests

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
  * do some necessary post processing steps: sheband, runpath, etc.
  * add conda metadata to the "build environment"
  * package up the new files in the "build environment" into a conda package
  * test the new conda package:
      - create a "test environment" with the package (and its dependencies)
      - run the test script
