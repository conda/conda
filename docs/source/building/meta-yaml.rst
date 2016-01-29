.. _meta-yaml:

The meta.yaml file
==================

.. contents:: Sections of ``meta.yaml``:

All the metadata in the conda build recipe is specified in the ``meta.yaml`` file, 
as in this example of a simple meta.yaml file:

.. literalinclude:: /build_tutorials/meta.yaml

NOTE: All sections are optional except for package/name and package/version.

NOTE: All headers should appear exactly once. If they appear multiple times, only 
the last will be remembered. For example, the "package:" header should only appear 
once in the file.

Package section
---------------

Package name
~~~~~~~~~~~~

Lower case name of package, may contain '-' but no spaces

.. code-block:: yaml

  package:
    name: bsdiff4

Package version
~~~~~~~~~~~~~~~

Version of package. Should use the PEP-386 verlib conventions. Note that YAML will 
interpret versions like 1.0 as floats, meaning that 0.10 will be the same as 0.1. To
avoid this, always put the version in quotes, so that it will be interpreted as a 
string.

.. code-block:: yaml

  package:
    version: "1.1.4"

NOTE: The version cannot contain a dash '-' character.

NOTE: Post-build versioning: In some cases, you may not know the version, build 
number, or build string of the package until after it is built. In this case, you 
can write files named ``__conda_version__.txt``, ``__conda_buildnum__.txt``, or 
``__conda_buildstr__.txt`` to the source directory, and the contents of the file 
will be used as the version, build number, or build string, respectively (and the 
respective metadata from the ``meta.yaml`` will be ignored).

Source section
--------------

The source section specifies where the source code of the package is coming from. 
The source may come from a tarball file, git, hg, or svn, may be a local path, 
and may contain patches.

Source from tarball
~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

  source:
    fn: bsdiff-1.1.14.tar.gz
    url: https://pypi.python.org/packages/source/b/bsdiff4/bsdiff4-1.1.4.tar.gz
    md5: 29f6089290505fc1a852e176bd276c43
    sha1: f0a2c9a30073449cfb7d171c57552f3109d93894
    sha256: 5a022ff4c1d1de87232b1c70bde50afbb98212fd246be4a867d8737173cf1f8f

NOTE: If you use ``url`` above, then ``fn`` is also required.

Source from git
~~~~~~~~~~~~~~~

The ``git_url`` can also be a relative path to the recipe directory:

.. code-block:: yaml

  source:
    git_url: https://github.com/ilanschnell/bsdiff4.git
    git_rev: 1.1.4

Source from hg
~~~~~~~~~~~~~~

.. code-block:: yaml

  source:
    hg_url: ssh://hg@bitbucket.org/ilanschnell/bsdiff4
    hg_tag: 1.1.4

Source from svn
~~~~~~~~~~~~~~~

.. code-block:: yaml

  source:
    svn_url: https://github.com/ilanschnell/bsdiff
    svn_rev: 1.1.4
    svn_ignore_externals: True # (defaults to False)

Source from a local path
~~~~~~~~~~~~~~~~~~~~~~~~

If the path is relative it is taken relative to the recipe directory. The source 
will be copied to the work directory before building:

.. code-block:: yaml

  source:
    path: ../src

Patches
~~~~~~~

Patches may optionally be applied to the source:

.. code-block:: yaml

  source:
    #[source information here]
    patches:
      - my.patch # the patch file is expected to be found in the recipe


Build section
-------------

Build number and string
~~~~~~~~~~~~~~~~~~~~~~~

The build number should be incremented for new builds of the same version. The number 
defaults to zero. The string defaults to the default conda build string plus the 
build number.

.. code-block:: yaml

  build:
    number: 1       
    string: abc

NOTE: The build string cannot contain a dash '-' character.

Python entry points
~~~~~~~~~~~~~~~~~~~

This creates a Python entry point named bsdiff4 that calls bsdiff4.cli.main_bsdiff4() .

.. code-block:: yaml

  build:
    entry_points:
      - bsdiff4 = bsdiff4.cli:main_bsdiff4
      - bspatch4 = bsdiff4.cli:main_bspatch4

Python.app
~~~~~~~~~~

If osx_is_app is set, entry points will use python.app instead of python in OS X. 
The default is False.

.. code-block:: yaml

  build:
    osx_is_app: True

Features
~~~~~~~~

Defines what features a package has.

SEE ALSO: :ref:`features` section below for additional information.

.. code-block:: yaml

  build:
    features:
      - feature1

Track features
~~~~~~~~~~~~~~

To enable a feature, a user should install a package that tracks that feature. A 
package can have a feature, or track that feature, or both, or neither. Usually 
it is best for the package that tracks a feature to be a metapackage that does 
not have the feature.

SEE ALSO: :ref:`features` section below for additional information.

.. code-block:: yaml

  build:
    track_features:
      - feature2

Preserve Python egg directory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is needed for some packages that use setuptools specific features. Default is False.

.. code-block:: yaml

  build:
    preserve_egg_dir: True

No link
~~~~~~~

A list of globs for files that should always be copied and never soft linked or hard linked.

.. code-block:: yaml

  build:
    no_link:
      - bin/*.py # Don't link any .py files in bin/

Script
~~~~~~

Used instead of build.sh or bld.bat. For short build scripts, this can be more convenient. 
You may need to use selectors (see below) to use different scripts for different platforms.

.. code-block:: yaml

  build:
    script: python setup.py install

RPATHs
~~~~~~

Set which RPATHs are used when making executables relocatable on Linux. The default is lib/

.. code-block:: yaml

  build:
    rpaths:
      - lib/
      - lib/R/lib/

NOTE: This is a Linux feature that is ignored on other systems.

Force files
~~~~~~~~~~~

Force files to always be included, even if they are already in the environment from the build dependencies. This may be needed, for instance, to create a recipe for conda itself.

.. code-block:: yaml

  build:
    always_include_files:
      - bin/file1
      - bin/file2

Relocation
~~~~~~~~~~

Advanced features. The following four keys (binary_relocation, detect_binary_files_with_prefix, has_prefix_files and binary_has_prefix_files) may be required to relocate files from the build environment to the installation environment.  See :ref:`relocatable` section below.

Binary relocation
~~~~~~~~~~~~~~~~~

Whether binary files should be made relocatable using install_name_tool on OS X or patchelf on Linux. Default is True.

.. code-block:: yaml

  build:
    binary_relocation: False

Detect binary files with prefix
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Binary files may contain the build prefix and need it replaced with the install prefix at installation time.  Conda can automatically identify and register such files. Default is False.

.. code-block:: yaml

  build:
    detect_binary_files_with_prefix: True

Binary has prefix files
~~~~~~~~~~~~~~~~~~~~~~~

You may also elect to specify files with prefixes individually:

.. code-block:: yaml

  build:
    binary_has_prefix_files:
      - bin/binaryfile1
      - lib/binaryfile2

Text files with prefix files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Text files (files containing no NULL bytes) may contain the build prefix and need it replaced with the install prefix at installation time.  Conda will automatically register such files.  Binary files that contain the  build prefix are generally handled differently (see binary_has_prefix_files or detect_binary_files_with_prefix), but there may be cases where such a binary file needs to be treated as an ordinary text file, in which case they need to be identified:

.. code-block:: yaml

  build:
    has_prefix_files:
      - bin/file1
      - lib/file2

Skipping builds
~~~~~~~~~~~~~~~

Whether conda-build should skip the build of this recipe. Particularly useful for defining recipes which are platform specific.
Default is False.

.. code-block:: yaml

  build:
    skip: True  # [not win]

Requirements section
--------------------

Versions for requirements must follow the Conda match specification. See :ref:`build-version-spec` .

The build and runtime requirements. Dependencies of these requirements are included automatically.

Build
~~~~~

Packages required to build the package. Python and NumPy must be listed explicitly if they are required.

.. code-block:: yaml

  requirements:
    build:
      - python

Some users may wish to build a recipe against different versions of NumPy and ensure that each version is part of the package dependencies, which can be done by listing ``numpy x.x`` as a requirement in meta.yaml and using ``conda build`` with a NumPy version option such as ``--numpy 1.7``. Note that the line in the meta.yaml file should literally say ``numpy x.x`` and should not have any numbers. If the meta.yaml file uses ``numpy x.x``, then it is required to use the ``--numpy`` option with ``conda build``.

.. code-block:: yaml

  requirements:
    build:
      - python
      - numpy x.x

Run
~~~

Packages required to run the package. These are the dependencies that will be installed automatically whenever the package is installed. Package names should follow the :ref:`build-version-spec` .

.. code-block:: yaml

  requirements:
    run:
      - python
      - argparse # [py26]
      - six >=1.8.0

Test section
------------

If this section exists or if there is a run_test.[py,pl,sh,bat] file in the recipe, the package will be installed into a test environment after the build is finished and the tests will be run there.

Test files
~~~~~~~~~~

Test files which are copied from the recipe into the (temporary) test directory which are needed during testing:

.. code-block:: yaml

  test:
    files:
      - test-data.txt

Test requirements
~~~~~~~~~~~~~~~~~

In addition to the runtime requirements, you can specify requirements needed during testing. The runtime requirements specified above are included automatically.

.. code-block:: yaml

  test:
    requires:
      nose

Test commands
~~~~~~~~~~~~~

Commands that are run as part of the test.

.. code-block:: yaml

  test:
    commands:
      - bsdiff4 -h
      - bspatch4 -h

Python imports
~~~~~~~~~~~~~~

List of Python modules or packages that will be imported in the test environment.

.. code-block:: yaml

  test:
    imports:
      - bsdiff4

This would be equivalent to having a run_test.py with

.. code-block:: python

  import bsdiff4

Run test script
~~~~~~~~~~~~~~~

The script run_test.sh (or .bat/.py/.pl) will be run automatically if it is part of the recipe.

.. code-block:: bash

  test:
    run_test.sh
    run_test.bat
    run_test.py
    run_test.pl

NOTE: Python or Perl .py/.pl scripts are only valid as part of Python/Perl packages, respectively.

About section
-------------

Identifying information about the package. Displays in Anaconda.org channel.

.. code-block:: yaml

  about:
    home: https://github.com/ilanschnell/bsdiff4
    license: BSD
    license_file: LICENSE
    summary: binary diff and patch using the BSDIFF4-format

License file
~~~~~~~~~~~~

A file containing the software license can be added to the package metadata.  Please note that many licenses require the license statement to be distributed with the package.  As a convenience, a value of True will use the first file found by looking in the source root directory for LICENSE, LICENSE.txt, license, or license.txt, in that order.  A value of False (the default) indicates no license file will be included in the package metadata.  The filename is relative to the source directory.

.. code-block:: yaml

  about:
    license_file: LICENSE

App section
-----------

If the app section is present, the package will be an app, meaning it will appear in the Anaconda Launcher.

Entry point
~~~~~~~~~~~

The command that is called to launch the app:

.. code-block:: yaml

  app:
    entry: ipython notebook

Icon file
~~~~~~~~~

The icon file contained in the recipe:

.. code-block:: yaml

  app:
    icon: icon_64x64.png

Summary
~~~~~~~

Summary of the package used in the launcher:

.. code-block:: yaml

  app:
    summary:  "The Jupyter Notebook"

Own environment
~~~~~~~~~~~~~~~

If own_environment is true, installing the app through the launcher will install into its own environment. The default is False.

.. code-block:: yaml

  app:
    own_environment: True

Extra section
-------------

The extra section is a schema-free area for storing non-conda specific metadata in standard YAML form.
For example, to store recipe maintainer information, one could do:

.. code-block:: yaml

  extra:
    maintainers:
     - name of maintainer


Preprocessing selectors
-----------------------

In addition, you can add selectors to any line, which are used as part of a
preprocessing stage. Before the yaml file is read, each selector is evaluated,
and if it is False, the line that it is on is removed.  A selector is of the
form ``# [<selector>]`` at the end of a line.

For example

.. code-block:: yaml

   source:
     url: http://path/to/unix/source    # [not win]
     url: http://path/to/windows/source # [win]

A selector is just a valid Python statement, that is executed.  The following
variables are defined. Unless otherwise stated, the variables are booleans.

.. list-table::

   * - ``linux``
     - True if the platform is Linux
   * - ``linux32``
     - True if the platform is Linux and the Python architecture is 32-bit
   * - ``linux64``
     - True if the platform is Linux and the Python architecture is 64-bit
   * - ``armv6``
     - True if the platform is Linux and the Python architecture is armv6l
   * - ``osx``
     - True if the platform is OS X
   * - ``unix``
     - True if the platform is Unix (OS X or Linux)
   * - ``win``
     - True if the platform is Windows
   * - ``win32``
     - True if the platform is Windows and the Python architecture is 32-bit
   * - ``win64``
     - True if the platform is Windows and the Python architecture is 64-bit
   * - ``py``
     - The Python version as a two digit string (like ``'27'``). See also the
       ``CONDA_PY`` environment variable :ref:`below <build-envs>`.
   * - ``py3k``
     - True if the Python major version is 3
   * - ``py2k``
     - True if the Python major version is 2
   * - ``py26``
     - True if the Python version is 2.6
   * - ``py27``
     - True if the Python version is 2.7
   * - ``py33``
     - True if the Python version is 3.3
   * - ``py34``
     - True if the Python version is 3.4
   * - ``np``
     - The NumPy version as a two digit string (like ``'17'``).  See also the
       ``CONDA_NPY`` environment variable :ref:`below <build-envs>`.

Because the selector is any valid Python expression, complicated logic is
possible.

.. code-block:: yaml

   source:
     url: http://path/to/windows/source      # [win]
     url: http://path/to/python2/unix/source # [unix and py2k]
     url: http://path/to/python3/unix/source # [unix and py3k]

Note that the selectors delete only the line that they are on, so you may
need to put the same selector on multiple lines.

.. code-block:: yaml

   source:
     url: http://path/to/windows/source     # [win]
     md5: 30fbf531409a18a48b1be249052e242a  # [win]
     url: http://path/to/unix/source        # [unix]
     md5: 88510902197cba0d1ab4791e0f41a66e  # [unix]

.. _features:

Features
--------

Features are a way to track differences in two packages that have the same
name and version.  For example, a feature might indicate a specialized
compiler or runtime, or a fork of a package. The canonical example of a
feature is the ``mkl`` feature in Anaconda Accelerate. Packages that are
compiled against MKL, such as NumPy, have the ``mkl`` feature set.  The
``mkl`` metapackage has the ``mkl`` feature set in ``track_features``, so that
installing it installs the ``mkl`` feature (the fact that the name of this
metapackage matches the name of the feature is a coincidence).

Features should be thought of as features of the environment the package is
installed into, not the package itself. The reason is that when a feature is
installed, conda will automatically change to a package with that feature if
it exists, for instance, when the ``mkl`` feature is installed, regular
``numpy`` is removed and the ``numpy`` package with the ``mkl`` feature is
installed.  Enabling a feature does not install any packages that are not
already installed, but it all future packages with that feature that are
installed into that environment will be preferred.

Feature names are independent of package names---it is a coincidence that
``mkl`` is both the name of a package and the feature that it tracks.

To install a feature, install a package that tracks it. To remove a feature,
use ``conda remove --features``.

It's a good idea to create a metapackage for ``track_features``.  If you add
``track_features`` to a package that also has versions without that feature,
then the versions without that feature will never be selected, because conda
will always add the feature when it is installed from the ``track_features``
specification if your package with the feature.

Instead, it is a good idea to create a separate metapackage. For instance, if
you want to create some packages with the feature ``debug``, you would create
several packages with

.. code-block:: yaml

   build:
     features:
       - debug

and then create a special metapackage

.. code-block:: yaml

   package:
     # This name doesn't have to be the same as the feature, but can avoid confusion if it is
     name: debug
     # This need not relate to the version of any of the packages with the
     # feature. It is just a version for this metapackage.
     version: 1.0

   build:
     track_features:
       - debug

.. or use conda install --features, blocking on https://github.com/conda/conda/issues/543

.. _relocatable:

Making packages relocatable
---------------------------

Often, the most difficult thing about building a conda package is making it
relocatable.  Relocatable means that the package can be installed into any
prefix.  Otherwise, the package would only be usable in the same environment
in which it was built.

Conda build does the following things automatically to make packages
relocatable:

- Binary object files are converted to use relative paths using
  ``install_name_tool`` on OS X and ``patchelf`` on Linux.

- Any text file (containing no NULL bytes) containing the build prefix or the
  placeholder prefix ``/opt/anaconda1anaconda2anaconda3`` is registered in the
  ``info/has_prefix`` file in the package metadata.  When conda installs the
  package, any files in ``info/has_prefix`` will have the registered prefix
  replaced with the install prefix.  See :ref:`package_metadata` for more
  information.

- Any binary file containing the build prefix can automatically be registered
  in ``info/has_prefix`` using ``build/detect_binary_files_with_prefix`` in
  ``meta.yaml``.  Alternatively, individual binary files can be registered by
  listing them in ``build/binary_has_prefix_files`` in meta.yaml.  The
  registered files will have their build prefix replaced with the install
  prefix at install time.  This works by padding the install prefix with null
  terminators, such that the length of the binary file remains the same.  The
  build prefix must therefore be long enough to accommodate any reasonable
  installation prefix. Whenever the ``build/binary_has_prefix_files`` list is
  not empty or ``build/detect_binary_files_with_prefix`` is set, conda will pad
  the build prefix (appending ``_placehold``\'s to the end of the build
  directory name) to 80 characters.

- There may be cases where conda identified a file as binary, but it needs to
  have the build prefix replaced as if it were text (no padding with null
  terminators). Such files can be listed in ``build/has_prefix_files`` in
  ``meta.yaml``.
