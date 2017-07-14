.. _meta-yaml:

============================
Defining metadata (meta.yml)
============================

.. contents::
   :local:
   :depth: 1


All the metadata in the conda build recipe is specified in the
``meta.yaml`` file, as in this simple example:

.. literalinclude:: ../../tutorials/meta.yaml

All sections are optional except for ``package/name`` and
``package/version``.

Headers must appear only once. If they appear multiple times,
only the last is remembered. For example, the ``package:`` header
should appear only once in the file.


Package section
===============

Specifies package information.

Package name
-------------

The lower case name of the package. It may contain "-", but no
spaces.

.. code-block:: yaml

   package:
     name: bsdiff4

Package version
---------------

The version number of the package. Use the PEP-386 verlib
conventions. Cannot contain "-". YAML interprets version numbers
such as 1.0 as floats, meaning that 0.10 will be the same as 0.1.
To avoid this, put the version number in quotes so that it is
interpreted as a string.

.. code-block:: yaml

   package:
     version: "1.1.4"

NOTE: Post-build versioning: In some cases, you may not know the
version, build number or build string of the package until after
it is built. In these cases, you can perform
:ref:`jinja-templates` or utilize :ref:`git-env` and
:ref:`inherited-env-vars`.


Source section
==============

Specifies where the source code of the package is coming from.
The source may come from a tarball file, git, hg or svn. It may
be a local path, and it may contain patches.


Source from tarball/zip archive
-------------------------------

.. code-block:: yaml

   source:
     url: https://pypi.python.org/packages/source/b/bsdiff4/bsdiff4-1.1.4.tar.gz
     md5: 29f6089290505fc1a852e176bd276c43
     sha1: f0a2c9a30073449cfb7d171c57552f3109d93894
     sha256: 5a022ff4c1d1de87232b1c70bde50afbb98212fd246be4a867d8737173cf1f8f


If an extracted archive contains only one folder at its top level, its contents
will be moved one level up so that the extracted package contents sit in the
root of the work folder.

Source from git
---------------

The git_url can also be a relative path to the recipe directory.

.. code-block:: yaml

   source:
     git_url: https://github.com/ilanschnell/bsdiff4.git
     git_rev: 1.1.4


Source from hg
--------------

.. code-block:: yaml

   source:
     hg_url: ssh://hg@bitbucket.org/ilanschnell/bsdiff4
     hg_tag: 1.1.4


Source from svn
---------------

.. code-block:: yaml

   source:
     svn_url: https://github.com/ilanschnell/bsdiff
     svn_rev: 1.1.4
     svn_ignore_externals: True # (defaults to False)


Source from a local path
-------------------------

If the path is relative, it is taken relative to the recipe
directory. The source is copied to the work directory before
building.

.. code-block:: yaml

   source:
     path: ../src

If the local path is a git or svn repository, you get the
corresponding environment variables defined in your build
environment. The only practical difference between git_url or
hg_url and path as source arguments is that git_url and hg_url
would be clones of a repository, while path would be a copy of
the repository. Using path allows you to build packages with
unstaged and uncommitted changes in the working directory.
git_url can build only up to the latest commit.


Patches
---------

Patches may optionally be applied to the source.

.. code-block:: yaml

   source:
     #[source information here]
     patches:
       - my.patch # the patch file is expected to be found in the recipe

Conda build automatically determines the patch strip level.

Destination path
~~~~~~~~~~~~~~~~

Within conda-build's work directory, you may specify a particular folder to
place source into. This feature is new in conda-build 3.0. Conda-build will
always drop you into the same folder (build folder/work), but it's up to you
whether you want your source extracted into that folder, or nested deeper. This
feature is particularly useful when dealing with multiple sources, but can apply
to recipes with single sources as well.

.. code-block:: yaml

  source:
    #[source information here]
    folder: my-destination/folder


Source from multiple sources
———-------------------------

Some software is most easily built by aggregating several pieces. For this,
conda-build 3.0 has added support for arbitrarily specifying many sources.

The syntax is a list of source dictionaries. Each member of this list
follows the same rules as the single source for earlier conda-build versions
(listed above). All features for each member are supported.

Example:

.. code-block:: yaml

  source:
    - url: https://package1.com/a.tar.bz2
      folder: stuff
    - url: https://package1.com/b.tar.bz2
      folder: stuff
    - git_url: https://github.com/conda/conda-build
      folder: conda-build

Here, the two URL tarballs will go into one folder, and the git repo
is checked out into its own space.

Note: Dashes denote list items in YAML syntax. Each of these
entries are extracted/cloned into one folder.

.. _meta-build:

Build section
=============

Each field that expect a path can also handle a glob pattern. The matching is
performed from the top of the build environment, so to match files inside
your project, use a pattern similar to the following one:
"\*\*/myproject/\*\*/\*.txt". This pattern will match any .txt file found in
your project.

NOTE: The quotation marks ("") are required for patterns that start with a \*.

Recursive globbing using \*\* is supported only in conda-build >= 3.0.

Build number and string
-----------------------

The build number should be incremented for new builds of the same
version. The number defaults to ``0``. The build string cannot
contain "-". The string defaults to the default conda build
string plus the build number.

.. code-block:: yaml

   build:
     number: 1
     string: abc


Python entry points
-------------------

The following example creates a Python entry point named
"bsdiff4" that calls ``bsdiff4.cli.main_bsdiff4()``.

.. code-block:: yaml

   build:
     entry_points:
       - bsdiff4 = bsdiff4.cli:main_bsdiff4
       - bspatch4 = bsdiff4.cli:main_bspatch4

Python.app
----------

If osx_is_app is set, entry points use ``python.app`` instead of
Python in macOS. The default is ``False``.

.. code-block:: yaml

   build:
     osx_is_app: True


Features
--------

Defines what features a package has. For more information, see
:doc:`features`.

.. code-block:: yaml

   build:
     features:
       - feature1


Track features
--------------

To enable a feature, install a package that tracks that feature.
A package can have a feature, track that feature, or both, or
neither. Usually it is best for the package that tracks a
feature to be a metapackage that does not have the feature. For
more information, see :doc:`features`.

.. code-block:: yaml

   build:
     track_features:
       - feature2


Preserve Python egg directory
-----------------------------

This is needed for some packages that use features specific to
setuptools. The default is ``False``.

.. code-block:: yaml

   build:
     preserve_egg_dir: True


Skip compiling some .py files into .pyc files
----------------------------------------------

Some packages ship ``.py`` files that cannot be compiled, such
as those that contain templates. Some packages also ship ``.py``
files that should not be compiled yet, because the Python
interpreter that will be used is not known at build time. In
these cases, conda build can skip attempting to compile these
files. The patterns used in this section do not need the \*\* to
handle recursive paths.

.. code-block:: yaml

   build:
     skip_compile_pyc:
      - "*/templates/*.py"          # These should not (and cannot) be compiled
      - "*/share/plugins/gdb/*.py"  # The python embedded into gdb is unknown


.. _no-link:

No link
-------

A list of globs for files that should always be copied and never
soft linked or hard linked.

.. code-block:: yaml

   build:
     no_link:
       - bin/*.py  # Don't link any .py files in bin/

Script
------

Used instead of ``build.sh`` or ``bld.bat``. For short build
scripts, this can be more convenient. You may need to use
:ref:`selectors <preprocess-selectors>` to use different scripts
for different platforms.

.. code-block:: yaml

   build:
     script: python setup.py install

RPATHs
------

Set which RPATHs are used when making executables relocatable on
Linux. This is a Linux feature that is ignored on other systems.
The default is ``lib/``.

.. code-block:: yaml

   build:
     rpaths:
       - lib/
       - lib/R/lib/


Force files
-----------

Force files to always be included, even if they are already in
the environment from the build dependencies. This may be needed,
for example, to create a recipe for conda itself.

.. code-block:: yaml

   build:
     always_include_files:
       - bin/file1
       - bin/file2


Relocation
----------

Advanced features. You can use the following 4 keys to control
relocatability files from the build environment to the
installation environment:

* binary_relocation.
* has_prefix_files.
* binary_has_prefix_files.
* ignore_prefix_files.

For more information, see :doc:`make-relocatable`.


Binary relocation
-----------------

Whether binary files should be made relocatable using
install_name_tool on macOS or patchelf on Linux. The
default is ``True``. It also accepts ``False``, which indicates
no relocation for any files, or a list of files, which indicates
relocation only for listed files.

.. code-block:: yaml

   build:
     binary_relocation: False


.. _detect-bin:

Detect binary files with prefix
--------------------------------

Binary files may contain the build prefix and need it replaced
with the install prefix at installation time. Conda can
automatically identify and register such files. The default is
``True``.

NOTE: The default changed from ``False`` to ``True`` in conda
build 2.0. Setting this to ``False`` means that binary
relocation---RPATH---replacement will still be done, but
hard-coded prefixes in binaries will not be replaced. Prefixes
in text files will still be replaced.

.. code-block:: yaml

   build:
     detect_binary_files_with_prefix: False

Windows handles binary prefix replacement very differently than
Unix systems such as macOS and Linux. At this time, we are
unaware of any executable or library that uses hardcoded
embedded paths for locating other libraries or program data on
Windows. Instead, Windows follows `DLL search path
rules <https://msdn.microsoft.com/en-us/library/7d83bc18.aspx>`_
or more natively supports relocatability using relative paths.
Because of this, conda ignores most prefixes. However, pip
creates executables for Python entry points that do use embedded
paths on Windows. Conda build thus detects prefixes in all files
and records them by default. If you are getting errors about
path length on Windows, you should try to disable
detect_binary_files_with_prefix. Newer versions of Conda,
such as recent 4.2.x series releases and up, should have no
problems here, but earlier versions of conda do erroneously try
to apply any binary prefix replacement.


.. _bin-prefix:

Binary has prefix files
-----------------------

By default, conda build tries to detect prefixes in all files.
You may also elect to specify files with binary prefixes
individually. This allows you to specify the type of file as
binary, when it may be incorrectly detected as text for some
reason. Binary files are those containing NULL bytes.

.. code-block:: yaml

   build:
     binary_has_prefix_files:
       - bin/binaryfile1
       - lib/binaryfile2


Text files with prefix files
----------------------------

Text files---files containing no NULL bytes---may contain the
build prefix and need it replaced with the install prefix at
installation time. Conda will automatically register such files.
Binary files that contain the build prefix are generally
handled differently---see :ref:`bin-prefix`---but there may be
cases where such a binary file needs to be treated as an ordinary
text file, in which case they need to be identified.

.. code-block:: yaml

   build:
     has_prefix_files:
       - bin/file1
       - lib/file2


Ignore prefix files
-------------------

Used to exclude some or all of the files in the build recipe from
the list of files that have the build prefix replaced with the
install prefix.

To ignore all files in the build recipe, use:

.. code-block:: yaml

   build:
     ignore_prefix_files: True

To specify individual filenames, use:

.. code-block:: yaml

   build:
     ignore_prefix_files:
       - file1

This setting is independent of RPATH replacement. Use the
:ref:`detect-bin` setting to control that behavior.


Skipping builds
---------------

Specifies whether conda build should skip the build of this
recipe. Particularly useful for defining recipes that are
platform specific. The default is ``False``.

.. code-block:: yaml

   build:
     skip: True  # [not win]


Architecture independent packages
---------------------------------

Allows you to specify "no architecture" when building a package,
thus making it compatible with all platforms and architectures.
Noarch packages can be installed on any platform.

Since conda-build 2.1, and conda 4.3, conda supports different
languages. Assigning the noarch key as ``generic`` tells
conda to not try any manipulation of the contents.

.. code-block:: yaml

      build:
        noarch: generic

``noarch: generic`` is most useful for packages such as static javascript assets
and source archives. For pure Python packages that can run on any Python
version, you can use the ``noarch: python`` value instead:

.. code-block:: yaml

     build:
       noarch: python

The legacy syntax for ``noarch_python`` is still valid, and should be
used when you need to be certain that your package will be installable where
conda 4.3 is not yet available. All other forms of noarch packages require
conda >=4.3 to install.

.. code-block:: yaml

   build:
     noarch_python: True


Include build recipe
--------------------

The full conda build recipe and rendered ``meta.yaml`` file is
included in the :ref:`package_metadata` by default. You can
disable this with:

.. code-block:: yaml

   build:
     include_recipe: False


Use environment variables
-------------------------

Normally the build script in ``build.sh`` or ``bld.bat`` does not
pass through environment variables from the command line. Only
environment variables documented in :ref:`env-vars` are seen by
the build script. To "white-list" environment variables that
should be passed through to the build script:

.. code-block:: yaml

   build:
     script_env:
       - MYVAR
       - ANOTHER_VAR

If a listed environment variable is missing from the environment
seen by the conda build process itself, a UserWarning is
emitted during the build process and the variable remains
undefined.


Requirements section
====================

Specifies the build and runtime requirements. Dependencies of
these requirements are included automatically.

Versions for requirements must follow the conda match
specification. See :ref:`build-version-spec` .


Build
-----

Packages required to build the package. Python and NumPy must be
listed explicitly if they are required.

.. code-block:: yaml

   requirements:
     build:
       - python


Run
---

Packages required to run the package. These are the dependencies
that are installed automatically whenever the package is
installed. Package names should follow the
:ref:`build-version-spec`.

.. code-block:: yaml

   requirements:
     run:
       - python
       - argparse # [py26]
       - six >=1.8.0

To build a recipe against different versions of NumPy and ensure
that each version is part of the package dependencies, list
``numpy x.x`` as a requirement in ``meta.yaml`` and use
``conda-build`` with a NumPy version option such as
``--numpy 1.7``.

The line in the ``meta.yaml`` file should literally say
``numpy x.x`` and should not have any numbers. If the
``meta.yaml`` file uses ``numpy x.x``, it is required to use the
``--numpy`` option with ``conda-build``.

.. code-block:: yaml

   requirements:
     run:
       - python
       - numpy x.x


.. _meta-test:

Test section
============

If this section exists or if there is a
``run_test.[py,pl,sh,bat]`` file in the recipe, the package is
installed into a test environment after the build is finished,
and the tests are run there.

Test files
----------

Test files that are copied from the recipe into the temporary
test directory and are needed during testing.

.. code-block:: yaml

   test:
     files:
       - test-data.txt


Source files
------------

Test files that are copied from the source work directory into
the temporary test directory and are needed during testing.

.. code-block:: yaml

   test:
     source_files:
       - test-data.txt
       - some/directory
       - some/directory/pattern*.sh

This capability was added in conda build 2.0.


Test requirements
------------------

In addition to the runtime requirements, you can specify
requirements needed during testing.

.. code-block:: yaml

   test:
     requires:
       - nose


Test commands
--------------

Commands that are run as part of the test.

.. code-block:: yaml

   test:
     commands:
       - bsdiff4 -h
       - bspatch4 -h


Python imports
--------------

List of Python modules or packages that will be imported in the
test environment.

.. code-block:: yaml

   test:
     imports:
       - bsdiff4

This would be equivalent to having a ``run_test.py`` with the
following:

.. code-block:: python

   import bsdiff4


Run test script
---------------

The script ``run_test.sh``---or ``.bat``, ``.py`` or
``.pl``---is run automatically if it is part of the recipe.

.. code-block:: bash

   test:
     run_test.sh
     run_test.bat
     run_test.py
     run_test.pl

NOTE: Python .py and Perl .pl scripts are valid only
as part of Python and Perl packages, respectively.


Outputs section
================

Explicitly specifies packaging steps. This section supports
multiple outputs, as well as different package output types. The
format is a list of mappings. Build strings for subpackages are
determined by their runtime dependencies. This support was added
in conda build 2.1.0.

.. code-block:: none

   outputs:
     - name: some-subpackage
     - name: some-other-subpackage


NOTE: If any output is specified in the outputs section, the
default packaging behavior of conda build is bypassed. In other
words, if any subpackage is specified, then you do not get the
normal top-level build for this recipe without explicitly
defining a subpackage for it. This is an alternative to the
existing behavior, not an addition to it. For more information,
see :ref:`implicit_metapackages`.


Specifying files to include in output
--------------------------------------

You can specify files to be included in the package in either of
two ways:

* Explicit file lists.

* Scripts that move files into the build prefix.

Explicit file lists are relative paths from the root of the
build prefix. Explicit file lists support glob expressions.
Directory names are also supported, and they recursively include
contents.

.. code-block:: none

   outputs:
     - name: subpackage-name
       files:
         - a-file
         - a-folder
         - *.some-extension
         - somefolder/*.some-extension

Scripts that create or move files into the build prefix can be
any kind of script. Known script types need only specify the
script name. Currently the list of recognized extensions is
py, bat, ps1 and sh.

.. code-block:: none

   outputs:
     - name: subpackage-name
       script: move-files.py

The interpreter command must be specified if the file extension
is not recognized.

.. code-block:: none

   outputs:
     - name: subpackage-name
       script: some-script.extension
       script_interpreter: program plus arguments to run script

For scripts that move or create files, a fresh copy of the
working directory is provided at the start of each script
execution. This ensures that results between scripts are
independent of one another.

NOTE: For either the file list or the script approach, having
more than 1 package contain a given file is not explicitly
forbidden, but may prevent installation of both packages
simultaneously. Conda disallows this condition, because it
creates ambiguous runtime conditions.


Subpackage requirements
------------------------

Subpackages support runtime and test requirements. Build
requirements are not supported, because subpackages are
created after the build phase is complete. If you need a tool to
accomplish subpackaging, put it in the top-level package
requirements/build section.

.. code-block:: none

   outputs:
     - name: subpackage-name
       requirements:
         - some-dep

Subpackage dependencies propagate to the top-level package if
and only if the subpackage is listed as a requirement.

EXAMPLE: In this example, the top-level package depends on both
``some-dep-that-will-propagate`` and ``some-dep`` as runtime
requirements.

.. code-block:: none

   requirements:
     run:
       - some-dep-that-will-propagate

   outputs:
     - name: some-dep-that-will-propagate
       requirements:
         - some-dep


.. _implicit_metapackages:

Implicit metapackages
----------------------

When viewing the top-level package as a collection of smaller
subpackages, it may be convenient to define the top-level
package as a composition of several subpackages. If you do this
and you do not define a subpackage name that matches the
top-level package/name, conda build creates a metapackage for
you. This metapackage has runtime requirements drawn from its
dependency subpackages, for the sake of accurate build strings.

EXAMPLE: In this example, a metapackage for ``subpackage-example``
will be created. It will have runtime dependencies on
``subpackage1``, ``subpackage2``, ``some-dep`` and
``some-other-dep``.

.. code-block:: none

   package:
     name: subpackage-example
     version: 1.0

   requirements:
     run:
       - subpackage1
       - subpackage2

   outputs:
     - name: subpackage1
       requirements:
         - some-dep
     - name: subpackage2
       requirements:
         - some-other-dep
     - name: subpackage3
       requirements:
         - some-totally-exotic-dep


Subpackage tests
------------------

You can test subpackages independently of the top-level package.
Independent test script files for each separate package are
specified under the subpackage's test section. These files
support the same formats as the top-level ``run_test.*`` scripts,
which are .py, .pl, .bat and .sh. These may be extended to
support other script types in the future.

.. code-block:: none

   outputs:
     - name: subpackage-name
       test:
         script: some-other-script.py


By default, the ``run_test.*`` scripts apply only to the
top-level package. To apply them also to subpackages, list them
explicitly in the script section:

.. code-block:: none

   outputs:
     - name: subpackage-name
       test:
         script: run_test.py


Test requirements for subpackages are not supported. Instead,
subpackage tests install their runtime requirements---but not the
run requirements for the top-level package---and the test-time
requirements of the top-level package.

EXAMPLE: In this example, the test for ``subpackage-name``
installs ``some-test-dep`` and ``subpackage-run-req``, but not
``some-top-level-run-req``.

.. code-block:: none

   requirements:
     run:
       - some-top-level-run-req

   test:
     requires:
       - some-test-dep

   outputs:
     - name: subpackage-name
       requirements:
         - subpackage-run-req
       test:
         script: run_test.py


Output type
-----------

Conda-build supports creating packages other than conda packages.
Currently that support includes only wheels, RPMs, .deb
files, but others may come as demand appears. If type is not
specified, the default value is ``conda``.

.. code-block:: none

   requirements:
     build:
       - wheel

   outputs:
     - name: name-of-wheel-package
       type: wheel

Currently you must include the wheel package in your top-level
requirements/build section in order to build wheels.

When specifying type, the name field is optional, and it defaults
to the package/name field for the top-level recipe.

.. code-block:: none

   requirements:
     build:
       - wheel

   outputs:
     - type: wheel

Conda build currently knows how to test only conda packages.
Conda build does support using Twine to upload packages to PyPI.
See the conda build help output for the list of arguments
accepted that will be passed through to Twine.

NOTE: You must use pip to install Twine in order for this to work.


.. _about-section:


About section
==============

Specifies identifying information about the package. The
information displays in the Anaconda.org channel.

.. code-block:: yaml

  about:
    home: https://github.com/ilanschnell/bsdiff4
    license: BSD
    license_file: LICENSE
    summary: binary diff and patch using the BSDIFF4-format


License file
-------------

Add a file containing the software license to the package
metadata.  Many licenses require the license statement to be
distributed with the package. The filename is relative to the
source directory.

.. code-block:: yaml

  about:
    license_file: LICENSE


App section
============

If the app section is present, the package is an app, meaning
that it appears in the Anaconda Launcher.


Entry point
--------------

The command that is called to launch the app.

.. code-block:: yaml

  app:
    entry: ipython notebook


Icon file
-----------

The icon file contained in the recipe.

.. code-block:: yaml

  app:
    icon: icon_64x64.png


Summary
--------

Summary of the package used in the launcher.

.. code-block:: yaml

  app:
    summary:  "The Jupyter Notebook"


Own environment
----------------

If ``True``, installing the app through the launcher installs
into its own environment. The default is ``False``.

.. code-block:: yaml

  app:
    own_environment: True


Extra section
==============

A schema-free area for storing non-conda-specific metadata in
standard YAML form.

EXAMPLE: To store recipe maintainer information:

.. code-block:: yaml

  extra:
    maintainers:
     - name of maintainer


.. _jinja-templates:

Templating with Jinja
=====================

Conda build supports Jinja templating in the ``meta.yaml`` file.

EXAMPLE: The following ``meta.yaml`` would work with the GIT
values defined for git repositores. The recipe is included at the
base directory of the git repository, so the git_url is ``../``:

.. code-block:: yaml

     package:
       name: mypkg
       version: {{ GIT_DESCRIBE_TAG }}

     build:
       number: {{ GIT_DESCRIBE_NUMBER }}

       # Note that this will override the default build string with the Python
       # and NumPy versions
       string: {{ GIT_BUILD_STR }}

     source:
       git_url: ../


Conda build checks if the jinja2 variables that you use are
defined and produces a clear error if it is not.

You can also use a different syntax for these environment
variables that allows default values to be set, although it is
somewhat more verbose.

EXAMPLE: A version of the previous example using the syntax that
allows defaults:

.. code-block:: yaml

     package:
       name: mypkg
       version: {{ environ.get('GIT_DESCRIBE_TAG', '') }}

     build:
       number: {{ environ.get('GIT_DESCRIBE_NUMBER', 0) }}

       # Note that this will override the default build string with the Python
       # and NumPy versions
       string: {{ environ.get('GIT_BUILD_STR', '') }}

     source:
       git_url: ../

One further possibility using templating is obtaining data from
your downloaded source code.

EXAMPLE: To process a project's ``setup.py`` and obtain the
version and other metadata:

.. code-block:: none

    {% set data = load_setup_py_data() %}

    package:
      name: conda-build-test-source-setup-py-data
      version: {{ data.get('version') }}

    # source will be downloaded prior to filling in jinja templates
    # Example assumes that this folder has setup.py in it
    source:
      path_url: ../

These functions are completely compatible with any other
variables such as git and mercurial.

Extending this arbitrarily to other functions requires that
functions be predefined before jinja processing, which in
practice means changing the conda build source code. See the
`conda build issue tracker
<https://github.com/conda/conda-build/issues>`_.

For more information, see the `Jinja2 template
documentation <http://jinja.pocoo.org/docs/dev/templates/>`_
and `the list of available environment
variables <https://conda.io/docs/building/environment-vars.html>`_.

Jinja templates are evaluated during the build process. To
retrieve a fully rendered ``meta.yaml`` use the
`../commands/build/conda-render`.


.. _preprocess-selectors:

Preprocessing selectors
=======================

You can add selectors to any line, which are used as part of a
preprocessing stage. Before the ``meta.yaml`` file is read, each
selector is evaluated, and if it is ``False``, the line that it
is on is removed. A selector has the form ``# [<selector>]`` at
the end of a line.

.. code-block:: yaml

   source:
     url: http://path/to/unix/source    # [not win]
     url: http://path/to/windows/source # [win]

NOTE: Preprocessing selectors are evaluated after Jinja templates.

A selector is a valid Python statement that is executed. The
following variables are defined. Unless otherwise stated, the
variables are booleans.

.. list-table::
   :widths: 20 80

   * - x86
     - True if the system architecture is x86, both 32-bit and
       64-bit, for Intel or AMD chips.
   * - x86_64
     - True if the system architecture is x86_64, which is
       64-bit, for Intel or AMD chips.
   * - linux
     - True if the platform is Linux.
   * - linux32
     - True if the platform is Linux and the Python architecture
       is 32-bit.
   * - linux64
     - True if the platform is Linux and the Python architecture
       is 64-bit.
   * - armv6l
     - True if the platform is Linux and the Python architecture
       is armv6l.
   * - armv7l
     - True if the platform is Linux and the Python architecture
       is armv7l.
   * - ppc64le
     - True if the platform is Linux and the Python architecture
       is ppc64le.
   * - osx
     - True if the platform is macOS.
   * - unix
     - True if the platform is Unix, either macOS or Linux.
   * - win
     - True if the platform is Windows.
   * - win32
     - True if the platform is Windows and the Python
       architecture is 32-bit.
   * - win64
     - True if the platform is Windows and the Python
       architecture is 64-bit.
   * - py
     - The Python version as a 2-digit string, such as ``'27'``.
       See the CONDA_PY :ref:`environment variable <build-envs>`.
   * - py3k
     - True if the Python major version is 3.
   * - py2k
     - True if the Python major version is 2.
   * - py27
     - True if the Python version is 2.7.
   * - py34
     - True if the Python version is 3.4.
   * - py35
     - True if the Python version is 3.5.
     * - py36
       - True if the Python version is 3.6.
   * - np
     - The NumPy version as an integer such as ``111``. See the
       CONDA_NPY :ref:`environment variable <build-envs>`.

Because the selector is any valid Python expression, complicated
logic is possible:

.. code-block:: yaml

   source:
     url: http://path/to/windows/source      # [win]
     url: http://path/to/python2/unix/source # [unix and py2k]
     url: http://path/to/python3/unix/source # [unix and py3k]

NOTE: The selectors delete only the line that they are on, so you
may need to put the same selector on multiple lines:

.. code-block:: yaml

   source:
     url: http://path/to/windows/source     # [win]
     md5: 30fbf531409a18a48b1be249052e242a  # [win]
     url: http://path/to/unix/source        # [unix]
     md5: 88510902197cba0d1ab4791e0f41a66e  # [unix]
