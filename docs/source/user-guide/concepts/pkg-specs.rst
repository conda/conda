=====================
Package specification
=====================

.. _package_metadata:

Package metadata
================

The ``info/`` directory contains all metadata about a package.
Files in this location are not installed under the install
prefix. Although you are free to add any file to this directory,
conda only inspects the content of the files discussed below.

Info
----

* files

  * a list of all the files in the package (not included in ``info/``)

* ``index.json``

  * metadata about the package including platform, version,
    dependencies, and build info

.. code-block:: bash

  {
    "arch": "x86_64",
    "build": "py37hfa4b5c9_1",
    "build_number": 1,
    "depends": [
      "depend > 1.1.1"
    ],
    "license": "BSD 3-Clause",
    "name": "fun-packge",
    "platform": "linux",
    "subdir": "linux-64",
    "timestamp": 1535416612069,
    "version": "0.0.0"
  }

* ``paths.json``

  * a list of files in the package, along with their associated SHA-256, size in bytes,
    and the type of path (eg. hardlink vs. softlink)

.. code-block:: bash

  {
    "paths": [
      {
        "_path": "lib/python3.7/site-packages/fun-packge/__init__.py",
        "path_type": "hardlink",
        "sha256": "76f3b6e34feeb651aff33ca59e0279c4eadce5a50c6ad93b961c846f7ba717e9",
        "size_in_bytes": 2067
      },
      {
        "_path": "lib/python3.7/site-packages/fun-packge/__config__.py",
        "path_type": "hardlink",
        "sha256": "348e3602616c1fe4c84502b1d8cf97c740d886002c78edab176759610d287f06",
        "size_in_bytes": 87519
      },
      ...
  }


info/index.json
---------------

This file contains basic information about the package, such as
name, version, build string, and dependencies. The content of this
file is stored in ``repodata.json``, which is the repository
index file, hence the name ``index.json``. The JSON object is a
dictionary containing the keys shown below. The filename of the
conda package is composed of the first 3 values, as in:
``<name>-<version>-<build>.tar.bz2``.

.. list-table::
   :widths: 15 15 50

   * - **Key**
     - **Type**
     - **Description**

   * - name
     - string
     - The lowercase name of the package. May contain the "-"
       character.

   * - version
     - string
     - The package version. May not contain "-". Conda
       acknowledges `PEP 440
       <https://www.python.org/dev/peps/pep-0440/>`_.

   * - build
     - string
     - The build string. May not contain "-". Differentiates
       builds of packages with otherwise identical names and
       versions, such as:

       * A build with other dependencies, such as Python 3.4
         instead of Python 2.7.
       * A bug fix in the build process.
       * Some different optional dependencies, such as MKL versus
         ATLAS linkage. Nothing in conda actually inspects the
         build string. Strings such as ``np18py34_1`` are
         designed only for human readability and conda never
         parses them.

   * - build_number
     - integer
     - A non-negative integer representing the build number of
       the package.

       Unlike the build string, the build_number is inspected by
       conda. Conda uses it to sort packages that have otherwise
       identical names and versions to determine the latest one.
       This is important because new builds that contain bug
       fixes for the way a package is built may be added to a
       repository.

   * - depends
     - list of strings
     - A list of dependency specifications, where each element
       is a string, as outlined in :ref:`build-version-spec`.

   * - arch
     - string
     - Optional. The architecture the package is built for.

       EXAMPLE: ``x86_64``

       Conda currently does not use this key.

   * - platform
     - string
     - Optional. The OS that the package is built for.

       EXAMPLE: ``osx``

       Conda currently does not use this key. Packages for a
       specific architecture and platform are usually
       distinguished by the repository subdirectory that contains
       them---see :ref:`repo-si`.

info/files
----------

Lists all files that are part of the package itself, 1 per line.
All of these files need to get linked into the environment. Any
files in the package that are not listed in this file are not
linked when the package is installed. The directory delimiter for
the files in ``info/files`` should always be "/", even on
Windows. This matches the directory delimiter used in the
tarball.


info/has_prefix
---------------

Optional file. Lists all files that contain a hard-coded build
prefix or placeholder prefix, which needs to be replaced by the
install prefix at installation time.

.. note::
   Due to the way the binary replacement works, the
   placeholder prefix must be longer than the install prefix.

Each line of this file should be either a path, in which case it
is considered a text file with the default placeholder
``/opt/anaconda1anaconda2anaconda3``, or a space-separated list
of placeholder, mode, and path, where:

* Placeholder is the build or placeholder prefix.
* Mode is either ``text`` or ``binary``.
* Path is the relative path of the file to be updated.

EXAMPLE: On Windows::

  "Scripts/script1.py"
  "C:\Users\username\anaconda\envs\_build" text "Scripts/script2.bat"
  "C:/Users/username/anaconda/envs/_build" binary "Scripts/binary"

EXAMPLE: On macOS or Linux::

  bin/script.sh
  /Users/username/anaconda/envs/_build binary bin/binary
  /Users/username/anaconda/envs/_build text share/text

.. note::
   The directory delimiter for the relative path must always
   be "/", even on Windows. The placeholder may contain either "\\"
   or "/" on Windows, but the replacement prefix will match the
   delimiter used in the placeholder. The default placeholder
   ``/opt/anaconda1anaconda2anaconda3`` is an exception, being
   replaced with the install prefix using the native path
   delimiter. On Windows, the placeholder and path always appear
   in quotes to support paths with spaces.

info/license.txt
----------------

Optional file. The software license for the package.

info/no_link
------------

Optional file. Lists all files that cannot be linked - either
soft-linked or hard-linked - into environments and are copied
instead.

info/about.json
---------------

Optional file. Contains the entries in the `about section <https://docs.conda.io/projects/conda-build/en/latest/resources/define-metadata.html#about-section>`_
of the ``meta.yaml`` file. The following keys are
added to ``info/about.json`` if present in the build recipe:

* home
* dev_url
* doc_url
* license_url
* license
* summary
* description
* license_family

info/recipe
-----------

A directory containing the full contents of the build recipe.

meta.yaml.rendered
------------------

The fully rendered build recipe. See
`conda render <https://docs.conda.io/projects/conda-build/en/latest/resources/commands/conda-render.html>`_.

This directory is present only when the the include_recipe flag
is ``True`` in the `build section <https://docs.conda.io/projects/conda-build/en/latest/resources/define-metadata.html#build-section>`_.


.. _repo-si:

Repository structure and index
==============================

A conda repository - or channel - is a directory tree, usually
served over HTTPS, which has platform subdirectories, each of
which contain conda packages and a repository index. The index
file ``repodata.json`` lists all conda packages in the platform
subdirectory. Use ``conda index`` to create such an index from
the conda packages within a directory. It is simple mapping of
the full conda package filename to the dictionary object in
``info/index.json`` described in `link scripts <https://docs.conda.io/projects/conda-build/en/latest/resources/link-scripts.html>`_.

In the following example, a repository provides the conda package
``misc-1.0-np17py27_0.tar.bz2`` on 64-bit Linux and 32-bit
Windows::

  <some path>/linux-64/repodata.json
                       repodata.json.bz2
                       misc-1.0-np17py27_0.tar.bz2
             /win-32/repodata.json
                     repodata.json.bz2
                     misc-1.0-np17py27_0.tar.bz2

.. note::
   Both conda packages have identical filenames and are
   distinguished only by the repository subdirectory that contains
   them.


.. _build-version-spec:

Package match specifications
============================

This match specification is not the same as the syntax used at
the command line with ``conda install``, such as
``conda install python=3.9``. Internally, conda translates the
command line syntax to the spec defined in this section.

EXAMPLE: python=3.9 is translated to python 3.9*.

Package dependencies are specified using a match specification.
A match specification is a space-separated string of 1, 2, or 3
parts:

* The first part is always the exact name of the package.

* The second part refers to the version and may contain special
  characters:

  * \| means OR.

    EXAMPLE: ``1.0|1.2`` matches version 1.0 or 1.2

  * \* matches 0 or more characters in the version string. In
    terms of regular expressions, it is the same as ``r".*"``.

    EXAMPLE: 1.0|1.4* matches 1.0, 1.4 and 1.4.1b2, but not 1.2.

  * <, >, <=, >=, == and != are relational operators on versions,
    which are compared using
    `PEP-440 <https://www.python.org/dev/peps/pep-0440/>`_.  For example,
    ``<=1.0`` matches ``0.9``, ``0.9.1``, and ``1.0``, but not ``1.0.1``.
    ``==`` and ``!=`` are exact equality.

    Pre-release versioning is also supported such that ``>1.0b4`` will match
    ``1.0b5`` and ``1.0rc1`` but not ``1.0b4`` or ``1.0a5``.

    EXAMPLE: <=1.0 matches 0.9, 0.9.1, and 1.0, but not 1.0.1.

  * , means AND.

    EXAMPLE: >=2,<3 matches all packages in the 2 series. 2.0,
    2.1 and 2.9 all match, but 3.0 and 1.0 do not.

  * , has higher precedence than \|, so >=1,<2|>3 means greater
    than or equal to 1 AND less than 2 or greater than 3, which
    matches 1, 1.3 and 3.0, but not 2.2.

  Conda parses the version by splitting it into parts separated
  by \|. If the part begins with <, >, =, or !, it is parsed as a
  relational operator. Otherwise, it is parsed as a version,
  possibly containing the "*" operator.

* The third part is always the exact build string. When there are
  3 parts, the second part must be the exact version.

Remember that the version specification cannot contain spaces,
as spaces are used to delimit the package, version, and build
string in the whole match specification. ``python >= 2.7`` is an
invalid match specification. Furthermore, ``python>=2.7`` is
matched as any version of a package named ``python>=2.7``.

When using the command line, put double quotes around any package
version specification that contains the space character or any of
the following characters: <, >, \*, or \|.

EXAMPLE::

  conda install numpy=1.11
  conda install numpy==1.11
  conda install "numpy>1.11"
  conda install "numpy=1.11.1|1.11.3"
  conda install "numpy>=1.8,<2"


Examples
--------

The OR constraint "numpy=1.11.1|1.11.3" matches with 1.11.1 or
1.11.3.

The AND constraint "numpy>=1.8,<2" matches with 1.8 and 1.9 but
not 2.0.

The fuzzy constraint numpy=1.11 matches 1.11, 1.11.0, 1.11.1,
1.11.2, 1.11.18, and so on.

The exact constraint numpy==1.11 matches 1.11, 1.11.0, 1.11.0.0,
and so on.

The build string constraint "numpy=1.11.2=*nomkl*" matches the
NumPy 1.11.2 packages without MKL but not the normal MKL NumPy
1.11.2 packages.

The build string constraint "numpy=1.11.1|1.11.3=py36_0" matches
NumPy 1.11.1 or 1.11.3 built for Python 3.6 but not any versions
of NumPy built for Python 3.5 or Python 2.7.

The following are all valid match specifications for
numpy-1.8.1-py27_0:

* numpy
* numpy 1.8*
* numpy 1.8.1
* numpy >=1.8
* numpy ==1.8.1
* numpy 1.8|1.8*
* numpy >=1.8,<2
* numpy >=1.8,<2|1.9
* numpy 1.8.1 py27_0
* numpy=1.8.1=py27_0

Version ordering
================

The ``class VersionOrder(object)`` implements an order relation
between version strings.

Version strings can contain the usual alphanumeric characters
(A-Za-z0-9), separated into components by dots and underscores. Empty
segments (i.e. two consecutive dots, a leading/trailing underscore)
are not permitted. An optional epoch number - an integer
followed by ``!`` - can precede the actual version string
(this is useful to indicate a change in the versioning
scheme itself). Version comparison is case-insensitive.

Supported version strings
-------------------------

Conda supports six types of version strings:

   * Release versions contain only integers, e.g. ``1.0``, ``2.3.5``.
   * Pre-release versions use additional letters such as ``a`` or ``rc``,
     for example ``1.0a1``, ``1.2.beta3``, ``2.3.5rc3``.
   * Development versions are indicated by the string ``dev``,
     for example ``1.0dev42``, ``2.3.5.dev12``.
   * Post-release versions are indicated by the string ``post``,
     for example ``1.0post1``, ``2.3.5.post2``.
   * Tagged versions have a suffix that specifies a particular
     property of interest, e.g. ``1.1.parallel``. Tags can be added
     to any of the preceding 4 types. As far as sorting is concerned,
     tags are treated like strings in pre-release versions.
   * An optional local version string separated by ``+`` can be appended
     to the main (upstream) version string. It is only considered
     in comparisons when the main versions are equal, but otherwise
     handled in exactly the same manner.


Predictable version ordering
----------------------------

To obtain a predictable version ordering, it is crucial to keep the
version number scheme of a given package consistent over time.
Conda considers prerelease versions as less than release versions.

* Version strings should always have the same number of components
  (except for an optional tag suffix or local version string).

* Letters/Strings indicating non-release versions should always
  occur at the same position.

Before comparison, version strings are parsed as follows:

  * They are first split into epoch, version number, and local version
    number at ``!`` and ``+`` respectively. If there is no ``!``,
    the epoch is set to 0. If there is no ``+``, the local version is
    empty.
  * The version part is then split into components at ``.`` and ``_``.
  * Each component is split again into runs of numerals and non-numerals
  * Subcomponents containing only numerals are converted to integers.
  * Strings are converted to lowercase, with special treatment for ``dev``
    and ``post``.
  * When a component starts with a letter, the fillvalue 0 is inserted
    to keep numbers and strings in phase, resulting in ``1.1.a1' == 1.1.0a1'``.
  * The same is repeated for the local version part.

Examples:

  ``1.2g.beta15.rc  =>  [[0], [1], [2, 'g'], [0, 'beta', 15], [0, 'rc']]``

  ``1!2.15.1_ALPHA  =>  [[1], [2], [15], [1, '_alpha']]``

The resulting lists are compared lexicographically, where the following
rules are applied to each pair of corresponding subcomponents:

  * Integers are compared numerically.
  * Strings are compared lexicographically, case-insensitive.
  * Strings are smaller than integers, except

      * ``dev`` versions are smaller than all corresponding versions of other types.

      * ``post`` versions are greater than all corresponding versions of other types.
  * If a subcomponent has no correspondent, the missing correspondent is
    treated as integer 0 to ensure ``'1.1' == 1.1.0'``.

The resulting order is::

   0.4
 == 0.4.0
 < 0.4.1.rc
 == 0.4.1.RC   # case-insensitive comparison
 < 0.4.1
 < 0.5a1
 < 0.5b3
 < 0.5C1      # case-insensitive comparison
 < 0.5
 < 0.9.6
 < 0.960923
 < 1.0
 < 1.1dev1    # special case ``dev``
 < 1.1a1
 < 1.1.0dev1  # special case ``dev``
 == 1.1.dev1   # 0 is inserted before string
 < 1.1.a1
 < 1.1.0rc1
 < 1.1.0
 == 1.1
 < 1.1.0post1 # special case ``post``
 == 1.1.post1  # 0 is inserted before string
 < 1.1post1   # special case ``post``
 < 1996.07.12
 < 1!0.4.1    # epoch increased
 < 1!3.1.1.6
 < 2!0.4.1    # epoch increased again

Some packages (most notably OpenSSL) have incompatible version conventions.
In particular, OpenSSL interprets letters as version counters rather than
pre-release identifiers. For OpenSSL, the relation ``1.0.1 < 1.0.1a   =>   True   # for OpenSSL``
holds, whereas conda packages use the opposite ordering.
You can work around this problem by appending a dash to plain
version numbers:

``1.0.1a  =>  1.0.1post.a      # ensure correct ordering for OpenSSL``
