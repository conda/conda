Build Variants
==============


The nature of binary compatibility (or lack thereof) means that unfortunately,
we need to build binary packages (and any package containing binaries) with
potentially several variants to support different usage environments. For
example, using Numpy's C API means that a package must be used with the same
version of Numpy as runtime that was used at build time.

There has been limited support for this for a long time: Python in both build
and run requirements resulted in a package that had python pinned to the version
of Python used at build time (with a corresponding addition to the filename like
py27). Similar support existed for numpy with the addition of an ``x.x`` pin in
the recipe after `Conda-build PR
573 <https://github.com/conda/conda-build/pull/573>`_ was merged. However, there
has not been general support until conda-build version 3.0, though there have
been many proposals (`Conda-build issue
1142 <https://github.com/conda/conda-build/issues/1142>`_).

As of conda-build 3.0, a new configuration scheme has been added, dubbed
"variants." Conceptually, this decouples pinning values from recipes, replacing
them with Jinja2 template variables. It adds support for the notion of
"compatible" pinnings, though that concept is currently still under heavy
development, to be integrated with ABI compatibility databases, such as `ABI
Laboratory <https://abi-laboratory.pro/>`_.


Creating conda-build variant input files
----------------------------------------

Variant input files are yaml files. They're mostly very flat. Keys are made
directly available in Jinja2 templates. As a result, keys in the yaml files must
be valid jinja2 variable names (no - characters allowed). There are some special
keys that behave differently and can be more nested:

* ``pin_run_as_build``: should be a list of package names. Any package listed
  here, and occurring in both the build environment and the run requirements,
  will be pinned in the output package to the version present in the build
  environment. This is a generalization of the ``numpy x.x`` spec.
* ``extend_keys``: specifies keys that should be aggregated, rather than
  clobbered, by later variants. These are detailed below in the `Extended keys`_
  section.
* ``runtimes``: detailed further in `Extra Jinja2 functions`_.

Search order for these files is the following:

1. a file named ``.conda_build_config.yaml`` in the user's HOME folder
2. an arbitrarily named file specified as the value for the
   ``conda_build_config`` key in your .condarc file
3. a file named ``.conda_build_config.yaml`` in the same folder as ``meta.yaml``
   with your recipe
4. Any additional files specified on the command line with the
   ``--variant-config-files`` or ``-m`` command line flags, which can be passed
   multiple times for multiple files. The ``conda build`` and ``conda render``
   commands accept these arguments.

Files found later in this search order clobber the values from earlier files.


Using variants with the conda-build API
---------------------------------------


Ultimately, a variant is just a dictionary. This dictionary is provided directly
to Jinja2 - you can use any declared key from your variant configuration in your
Jinja2 templates. There are two ways that you can feed this information into the
API:

1. pass the ``variants`` keyword argument to API functions. Currently, the
   ``build``, ``render``, ``get_output_file_path``, and ``check`` functions
   accept this argument. ``variants`` should be a dictionary with values being
   lists of versions to iterate over. These are aggregated as detailed in the
   Aggregation of multiple variants section below.

2. Set the ``variant`` member of a Config object. This is just a simple
   dictionary. The values for fields should be strings, except "extended keys",
   which are documented in the `Extended keys`_ section below.

CONDA_* variables and command line arguments to conda-build
-----------------------------------------------------------

To ensure legacy consistency, environment variables such as CONDA_PY behave as
they always have, and they clobber all variants set in files or passed to the
API.

The full list of respected environment variables are:

* CONDA_PY
* CONDA_NPY
* CONDA_R
* CONDA_PERL
* CONDA_LUA

Legacy CLI flags are also still available. These are sticking around for their
usefulness in one-off jobs.

* --python
* --numpy
* --R
* --perl
* --lua


Aggregation of multiple variants
--------------------------------

The matrix of all variants is first consolidated from several dicts of lists
into a single dict of lists, and then transformed in a list of dicts (via the
Cartesian product of lists), where each value is a single string from the list
of potential values.

For example, general input for ``variants`` could be something like:

.. code-block:: python

    a = {'python': ['2.7', '3.5'], 'numpy': ['1.10', '1.11']}
    # values can be strings or lists.  Strings are converted to one-element lists internally.
    b = {'python': ['3.4', '3.5'], 'numpy': '1.11'}


Here, let's say b is found after a, and thus has priority over a. Merging these
two variants yields:

.. code-block:: python

    merged = {'python': ['3.4', '3.5'], 'numpy': ['1.11']}


``b``'s values for ``python`` have clobbered ``a``'s. From here, we compute the
Cartesian product of all input variables. The end result is a collection of
dicts, each with a string for each value. Output would be something like:

.. code-block:: python

    variants = [{'python': '3.4', 'numpy': '1.11'}, {'python': '3.5', 'numpy': '1.11'}]


and conda-build would loop over these variants where appropriate (building,
outputting package output names, etc.)

If ``numpy`` had had two values instead of one, we'd end up with *four* output
variants: 2 variants for ``python``, *times* two variants for ``numpy``:

    variants = [{'python': '3.4', 'numpy': '1.11'}, {'python': '3.5', 'numpy': '1.11'},
                {'python': '3.4', 'numpy': '1.10'}, {'python': '3.5', 'numpy': '1.10'}]


Bootstrapping pins based on an existing environment
---------------------------------------------------


To establish your initial variant, you may point at an existing conda
environment. Conda-build will examine the contents of that environment and pin
to the exact requirements that make up that environment.

.. code-block:: shell

   conda build --bootstrap name_of_env


You may specify either environment name (and depend on conda's environment
lookup) or filesystem path to the environment.


Extended keys
-------------


These are not looped over to establish the build matrix. Rather, they are
aggregated from all input variants, and each derived variant shares the whole
set. These are used internally for tracking which requirements should be pinned,
for example, with the ``pin_run_as_build`` key. You can add your own extended
keys by passing in values for the ``extend_keys`` key for any variant.


Appending to recipes
--------------------


As of conda-build 3.0, you can add a file named ``recipe_append.yaml`` in the
same folder as your ``meta.yaml`` file. This file is considered to follow the
same rules as meta.yaml, except that selectors and Jinja2 templates are not
(currently) evaluated. That will likely be added in future development.

Any contents in ``recipe_append.yaml`` will add to the contents of meta.yaml.
List values will be extended, and string values will be concatenated.


Partially clobbering recipes
----------------------------


As of conda-build 3.0, you can add a file named ``recipe_clobber.yaml`` in the
same folder as your ``meta.yaml`` file. This file is considered to follow the
same rules as meta.yaml, except that selectors and Jinja2 templates are not
(currently) evaluated. That will likely be added in future development.

Any contents in ``recipe_clobber.yaml`` will replace the contents of meta.yaml.
This can be useful, for example, for replacing the source URL without copying
the rest of the recipe into a fork.


Differentiating packages built with different variants
------------------------------------------------------


With only a few things supported, we could just add things to the filename, such
as py27 for python, or np111 for numpy. In the general case, which variants are
meant to support, this is no longer an option. Instead, part of the recipe is
hashed, and that hash is a unique identifier. The information that went into the
hash is stored with the package, in a file at ``info/hash_input.json``.
Currently, only the first 4 characters of the hash are stored. Output package
names will keep the pyXY and npXYY for now, but have added the 4-character hash.
Your package names will look like:

``my-package-1.0-py27h3142_0.tar.bz2``

Since conflicts only need to be prevented within one version of a package, we
think this will be adequate. If you run into hash collisions with this limited
subspace, please file an issue on the conda-build issue tracker.

The information that goes into this hash is currently defined in conda-build's
metadata.py module; the _get_hash_dictionary member function. This function
captures the following information:

* ``source`` section
* ``requirements`` section
* ``build`` section, except:
  * ``number``
  * ``string``

All "falsey" values (e.g. empty list values) are removed.

There is a CLI tool that just pretty-prints this json file for easy viewing:

*TODO*: Before release, this tool should be added!


Extra Jinja2 functions
----------------------


Two especially common operations when dealing with these API and ABI
incompatibilities are ways of specifying such compatibility, and of explicitly
expressing the compiler to be used. Three new Jinja2 functions are available when
evaluating ``meta.yaml`` templates:

* ``pin_compatible``: To be used as pin in run and/or test requirements. Takes
  package name argument. Looks up compatibility of named package installed in
  the build environment, and writes compatible range pin for run and/or test
  requirements.  Presently primarily only a semver-based assumption:
  ``>=(current version),<(next minor version)``. This will be enhanced as time
  goes on with information from `ABI Laboratory <https://abi-laboratory.pro/>`_

* ``compiler``: To be used in build requirements most commonly. Run or test as
  necessary. Takes language name argument. This is shorthand to facilitate cross
  compiler usage. This Jinja2 function ties together two variant variables,
  ``{language}_compiler`` and ``target_platform``, and outputs a single compiler
  package name. For example, this could be used to compile outputs targeting
  x86_64 and arm in one recipe, with a variant.

* ``runtime``: To be used in run requirements most commonly. Adds the correct
  runtime dependency based on similar logic to the compiler function. The
  runtime function depends on a map in the variant of compiler package name to
  runtime package name. There are limited defaults set in conda-build - for
  example ``g++`` as the compiler package on linux leads to runtime dependency
  on the ``libstdc++`` package.  For any non-default, you need to add a mapping
  from compiler package name to runtime package name (and possibly also version),
  as shown below.

.. code-block:: python

   variants = {'cxx_compiler': ['g++_linux-64'], 'target_platform': ['linux-64', 'linux-aarch64'],
                'runtimes': {'g++_linux-64_linux-64': 'libstdc++'}

and a meta.yaml file:

.. code-block:: yaml

   package:
       name: compiled-code
       version: 1.0

   requirements:
       build:
           - {{ compiler('cxx') }}
       run:
           - {{ runtime('cxx') }}

There are default "native" compilers that are used when no compiler is specified
in any variant.

This assumes that you have created two compiler packages named
``g++_linux-64_linux-64`` and ``g++_linux-64_linux-aarch64`` - all conda-build
is providing you with is a way to loop over appropriately named cross-compiler
toolchains.

Over time, conda-build will require that all packages explicitly list their
compiler requirements this way. This is to both simplify conda-build and improve
the tracking of metadata associated with compilers - localize it to compiler
packages, even if those packages are doing nothing more than activating an
already-installed compiler (such as Visual Studio.)

The compiler function is how you could support a non-standard Visual Studio
version, such as using VS 2015 to compile Python 2.7 and packages for Python
2.7. To accomplish this, you need to add the ``{{ compiler('<language>') }}`` to
each recipe that will make up the system.  Environment consistency is maintained
through dependencies - thus it is useful to have the runtime be a versioned
package, with only one version being able to be installed at a time. For
example, the ``vc`` package, originally created by Conda-Forge, is a versioned
package (only one version can be installed at a time), and it installs the
correct runtime package. By using this as the runtime on Windows, conda-build is
able to use the ``{{ runtime('c') }}`` to pin and keep binary compatibility.

Given these guidelines, a system of recipes using a variant like:

.. code-block:: python

   variants = {'cxx_compiler': ['vs2015']}


and meta.yaml contents like:

.. code-block:: yaml

   package:
       name: compiled-code
       version: 1.0

   requirements:
       build:
           # these are the same (and thus redundant) on windows, but different elsewhere
           - {{ compiler('c') }}
           - {{ compiler('cxx') }}
       run:
           # these are the same (and thus redundant) on windows, but different elsewhere
           - {{ runtime('c') }}
           - {{ runtime('cxx') }}


will create a system of packages that are all built with the VS 2015 compiler,
rather than whatever default is associated with the python version.
