Build Variants
==============

The nature of binary compatibility (and incompatibility) means that we
sometimes need to build binary packages (and any package containing binaries)
with several variants to support different usage environments. For
example, using Numpy's C API means that a package must be used with the same
version of Numpy at runtime that was used at build time.

There has been limited support for this for a long time. Including Python in
both build and run requirements resulted in a package with Python pinned to the
version of Python used at build time, and a corresponding addition to the
filename such as "py27". Similar support existed for numpy with the addition of
an ``x.x`` pin in the recipe after `Conda-build PR
573 <https://github.com/conda/conda-build/pull/573>`_ was merged. Before
conda-build version 3.0 there were also many longstanding proposals for general
support (`Conda-build issue
1142 <https://github.com/conda/conda-build/issues/1142>`_).

As of conda-build 3.0, a new configuration scheme has been added, dubbed
"variants." Conceptually, this decouples pinning values from recipes, replacing
them with Jinja2 template variables. It adds support for the notion of
"compatible" pinnings to be integrated with ABI compatibility databases, such as
`ABI Laboratory <https://abi-laboratory.pro/>`_. Note that the concept of
"compatible" pinnings is currently still under heavy development.

Variant input is ultimately a dictionary. These dictionaries are mostly very
flat. Keys are made directly available in Jinja2 templates. As a result, keys
in the dictionary (and in files read into dictionaries) must be valid jinja2
variable names (no ``-`` characters allowed). This example builds python 2.7
and 3.5 packages in one build command:

conda_build_config.yaml like:

.. code-block:: yaml

   python:
       - 2.7
       - 3.5


meta.yaml contents like:

.. code-block:: yaml

   package:
       name: compiled-code
       version: 1.0

   requirements:
       build:
           - python {{ python }}
       run:
           - python


The command to build recipes is unchanged relative to earlier conda-build
versions. For example, with our shell in the same folder as meta.yaml and
conda_build_config.yaml, we just call the ``conda build .`` command.


General pinning examples
------------------------

There are a few characteristic use cases for pinning.  Please consider this a
map for the content below.

1. Shared library providing a binary interface. All uses of this library use
   the binary interface. It is convenient to apply the same pin to all of your
   builds. Example: boost

   conda_build_config.yaml in your HOME folder:

   .. code-block:: yaml

      boost:
        - 1.61
        - 1.63
      pin_run_as_build:
        boost: x.x

   meta.yaml:

   .. code-block:: yaml

      package:
          name: compiled-code
          version: 1.0

      requirements:
          build:
              - boost  {{ boost }}
          run:
              - boost

   This example demonstrates several features:

   * user-wide configuration with a specifically named config file
     (conda_build_config.yaml in your home folder). More options below in
     `Creating conda-build variant config files`_.
   * building against multiple versions of a single library (set versions
     installed at build time)
   * pinning runtime requirements to the version used at build time. More
     information below at `Pinning at the variant level`_.
   * specify granularity of pinning. ``x.x`` pins major and minor version. More
     information at `Pinning expressions`_.


2. Python package with externally accessible binary component. Not all uses of
   this library use the binary interface (some only use pure Python). Example:
   numpy

   conda_build_config.yaml in your recipe folder (alongside meta.yaml):

   .. code-block:: yaml

      numpy:
        - 1.11
        - 1.12


   meta.yaml:

   .. code-block:: yaml

      package:
          name: numpy_using_pythonAPI_thing
          version: 1.0

      requirements:
          build:
              - python
              - numpy
          run:
              - python
              - numpy

   This example demonstrates a particular feature: reduction of builds when pins
   are unnecessary. Since the example recipe above only requires the Python API
   to numpy, we will only build the package once and the version of numpy will
   not be pinned at runtime to match the compile-time version.  There's more
   information at `Avoiding unnecessary builds`_.

   For a different package that makes use of the numpy C API, we will need to
   actually pin numpy in this recipe (and only in this recipe, so that other
   recipes don't unnecessarily build lots of variants).  To pin numpy, you can
   use the variant key directly in meta.yaml:

   .. code-block:: yaml

      package:
          name: numpy_using_cAPI_thing
          version: 1.0

      requirements:
          build:
              - numpy  {{ numpy }}
          run:
              - numpy  {{ numpy }}

   For legacy compatibility, python is pinned implicitly without specifying
   ``{{ python }}`` in your recipe. This is generally intractable to extend to
   all package names, so in general, try to get in the habit of always using
   the jinja2 variable substitution for pinning using versions from your
   conda_build_config.yaml file.

   There are also more flexible ways to pin, using the `Pinning expressions`_.
   See `Pinning at the recipe level`_ for examples.


3. One recipe splits into multiple packages, and package dependencies need to be
   dynamically pinned among one another. Example:
   GCC/libgcc/libstdc++/gfortran/etc.

   The dynamic pinning is the tricky part. Conda-build provides new ways to
   refer to other subpackages within a single recipe.

   .. code-block:: yaml

      package:
          name: dynamic_supackage
          version: 1.0

      requirements:
          run:
              - {{ pin_subpackage('my_awesome_subpackage') }}

      outputs:
        - name: my_awesome_subpackage
          version: 2.0

   By referring to subpackages this way, you don't need to worry about what the
   end version of my_awesome_subpackage will be. Update it independently and
   just let conda build figure it out and keep things consistent. There's more
   information below in the `Referencing subpackages`_ section.


Transition guide
----------------

Let's say we have a set of recipes that currently builds a C library, as well as
python and R bindings to that C library. xgboost, a recent machine learning
library, is one such example. Under conda-build 2.0 and earlier, you needed to
have three recipes - one for each component. Let's go over some simplified
meta.yaml files.  First, the C library:

.. code-block:: yaml

   package:
       name: libxgboost
       version: 1.0


Next, the python bindings:


.. code-block:: yaml

   package:
       name: py-xgboost
       version: 1.0

   requirements:
       build:
           - libxgboost  # you probably want to pin the version here, but there's no dynamic way to do it
           - python
       run:
           - libxgboost  # you probably want to pin the version here, but there's no dynamic way to do it
           - python


.. code-block:: yaml

   package:
       name: r-xgboost
       version: 1.0

   requirements:
       build:
           - libxgboost  # you probably want to pin the version here, but there's no dynamic way to do it
           - r-base
       run:
           - libxgboost  # you probably want to pin the version here, but there's no dynamic way to do it
           - r-base

To build these, you'd need several conda-build commands, or a tool like
conda-build-all to build out the various python versions. With conda-build 3.0
and split packages from conda-build 2.1, we can simplify this to one coherent
recipe that also includes the matrix of all desired python and R builds.

First, the meta.yaml file:

.. code-block:: yaml

   package:
       name: xgboost
       version: 1.0

   outputs:
       - name: libxgboost
       - name: py-xgboost
         requirements:
             - {{ pin_subpackage('libxgboost', exact=True) }}
             - python  {{ python }}

       - name: r-xgboost
         requirements:
             - {{ pin_subpackage('libxgboost', exact=True)
             - r-base  {{ r_base }}

Next, the conda_build_config.yaml file, specifying our build matrix:

.. code-block:: yaml

    python:
        - 2.7
        - 3.5
        - 3.6
    r_base:
        - 3.3.2
        - 3.4.0

With this updated method, you get a complete build matrix: 6 builds total. One
libxgboost library, 3 python versions, and 2 R versions. Additionally, the
python and R packages will have exact pins to the libxgboost package that was
built by this recipe.


.. _conda-build-variant-config-files:

Creating conda-build variant config files
-----------------------------------------

Variant input files are yaml files.  Search order for these files is the following:

1. a file named ``conda_build_config.yaml`` in the user's HOME folder
2. an arbitrarily named file specified as the value for the
   ``conda_build/config_file`` key in your .condarc file
3. a file named ``conda_build_config.yaml`` in the same folder as ``meta.yaml``
   with your recipe
4. Any additional files specified on the command line with the
   ``--variant-config-files`` or ``-m`` command line flags, which can be passed
   multiple times for multiple files. The ``conda build`` and ``conda render``
   commands accept these arguments.

Values in files found later in this search order will overwrite and replace the
values from earlier files.

NOTE: The key ``conda_build/config_file`` is a nested value::

    conda_build:
      config_file: some/path/to/file


Using variants with the conda-build API
---------------------------------------

Ultimately, a variant is just a dictionary. This dictionary is provided directly
to Jinja2, and you can use any declared key from your variant configuration in
your Jinja2 templates. There are two ways that you can feed this information
into the API:

1. Pass the ``variants`` keyword argument to API functions. Currently, the
   ``build``, ``render``, ``get_output_file_path``, and ``check`` functions
   accept this argument. ``variants`` should be a dictionary where each value
   is a list of versions to iterate over. These are aggregated as detailed in
   the `Aggregation of multiple variants`_ section below.

2. Set the ``variant`` member of a Config object. This is just a dictionary. The
   values for fields should be strings or lists of strings, except "extended
   keys", which are documented in the `Extended keys`_ section below.


Again, with meta.yaml contents like:

.. code-block:: yaml

   package:
       name: compiled-code
       version: 1.0

   requirements:
       build:
           - python {{ python }}
       run:
           - python {{ python }}

You could supply a variant to build this recipe like so:

.. code-block:: python

   variants = {'python': ['2.7', '3.5']}
   api.build(path_to_recipe, variants=variants)


Note that these Jinja2 variable substitutions are not limited to version
numbers. You can use them anywhere, for any string value. For example, to build
against different MPI implementations:

With meta.yaml contents like:

.. code-block:: yaml

   package:
       name: compiled-code
       version: 1.0

   requirements:
       build:
           - {{ mpi }}
       run:
           - {{ mpi }}


You could supply a variant to build this recipe like this (conda_build_config.yaml):


.. code-block:: yaml

    mpi:
        - openmpi  # version spec here is totally valid, and will apply in the recipe
        - mpich  # version spec here is totally valid, and will apply in the recipe

Selectors are valid in conda_build_config.yaml, so you can have one
conda_build_config.yaml for multiple platforms:

.. code-block:: yaml

    mpi:
        - openmpi  # [osx]
        - mpich    # [linux]
        - msmpi    # [win]


Jinja is not allowed in conda_build_config.yaml, though. It is the source of
information to feed into other jinja templates, and the buck has to stop
somewhere.


About reproducibility
---------------------

A critical part of any build system is ensuring that you can reproduce the same
output at some future point in time. This is often essential for troubleshooting
bugs. For example, if a package contains only binaries, it is helpful to
understand what source code created those binaries, and thus what bugs might be
present.

Since conda-build 2.0, conda-build has recorded its rendered meta.yaml files
into the ``info/recipe`` folder of each package it builds. Conda-build 3.0 is no
different in this regard, but the meta.yaml that is recorded is a frozen set of
the variables that make up the variant for that build.

Note that package builders may disable including the recipe with the
``build/include_recipe`` key in meta.yaml. If the recipe is omitted from the
package, then the package is not reproducible without the source recipe.


Special variant keys
--------------------

There are some special keys that behave differently and can be more nested:

* ``zip_keys``: a list of strings or a list of lists of strings. Strings are
  keys in variant. These couple groups of keys, so that particular keys are
  paired, rather than forming a matrix. This is useful, for example, to couple
  vc version to python version on Windows. More info below in the `Coupling
  keys`_ section.
* ``pin_run_as_build``: should be a dictionary. Keys are package names. Values
  are "pinning expressions" - explained in more detail in `Customizing
  compatibility`_. This is a generalization of the ``numpy x.x`` spec, so that
  you can pin your packages dynamically based on the versions used at build
  time.
* ``extend_keys``: specifies keys that should be aggregated, and not replaced,
  by later variants. These are detailed below in the `Extended keys`_
  section.
* ``ignore_version``: list of package names whose versions should be excluded
  from meta.yaml's requirements/build when computing hash. Described further in
  `Avoiding unnecessary builds`_.


Coupling keys
-------------

Sometimes particular versions need to be tied to other versions. For example, on
Windows, we generally follow the upstream Python.org association of Visual
Studio compiler version with Python version. Python 2.7 is always compiled with
Visual Studio 2008 (also known as MSVC 9). We don't want a
conda_build_config.yaml like the following to create a matrix of python/MSVC
versions:

.. code-block:: yaml

   python:
     - 2.7
     - 3.5
   vc:
     - 9
     - 14

Instead, we want 2.7 to be associated with 9, and 3.5 to be associated with 14.
The ``zip_keys`` key in conda_build_config.yaml is the way to achieve this:

.. code-block:: yaml

   python:
     - 2.7
     - 3.5
   vc:
     - 9
     - 14
   zip_keys:
     - python
     - vc

You can also have nested lists to achieve multiple groups of ``zip_keys``:

.. code-block:: yaml

   zip_keys:
     -
       - python
       - vc
     -
       - numpy
       - blas

The rules for ``zip_keys`` are:

1. Every list in a group must be the same length. This is because without
   equal length, there is no way to associate earlier elements from the
   shorter list with later elements in the longer list. For example, this is
   invalid, and will raise an error:

   .. code-block:: yaml

      python:
        - 2.7
        - 3.5
      vc:
        - 9
      zip_keys:
        - python
        - vc

2. ``zip_keys`` must be either a list of strings, or a list of lists of
   strings. You can't mix them.  For example, this is an error:

.. code-block:: yaml

   zip_keys:
     -
       - python
       - vc
     - numpy
     - blas

Rule #1 raises an interesting use case: How does one combine CLI flags
like --python with ``zip_keys``? Such a CLI flag will change the variant so that
it has only a single entry, but it will not change the ``vc`` entry in the
variant configuration. We'll end up with mismatched list lengths, and an error.
To overcome this, you should instead write a very simple YAML file with
all involved keys. Let's call it ``python27.yaml``, to reflect its intent:

.. code-block:: yaml

   python:
     - 2.7
   vc:
     - 9

Provide this file as a command-line argument:

.. code-block:: shell

    conda build recipe -m python27.yaml

You can also specify variants in JSON notation from the CLI as detailed in the
:ref:`CLI_vars` section. For example:

.. code-block:: shell

    conda build recipe --variants "{'python': ['2.7', '3.5'], 'vc': ['9', '14']}"


Avoiding unnecessary builds
---------------------------

To avoid building variants of packages where pinning does not require having
different builds, you can use the ``ignore_version`` key in your variant. Then
all variants are evaluated, but if any hashes are the same, then they are
considered duplicates, and are deduplicated. By omitting some packages from the
build dependencies, we can avoid creating unnecessarily specific hashes, and
allow this deduplication.

For example, let's consider a package that uses numpy in both run and build
requirements, and a variant that includes two numpy versions:

.. code-block:: python

    variants = [{'numpy': ['1.10', '1.11'], 'ignore_version': ['numpy']}]

meta.yaml:

.. code-block:: yaml

   requirements:
       build:
           - numpy {{ numpy }}
       run:
           - numpy

Here, the variant says that we'll have two builds - one for each numpy version.
However, since this recipe does not pin numpy's run requirement (because it
doesn't utilize numpy's C API), it is unnecessary to build it against both numpy
1.10 and 1.11.

The rendered form of this recipe, with conda-build ignoring numpy's value in the
recipe, is going to be just one build, that looks like:

meta.yaml:

.. code-block:: yaml

   requirements:
       build:
           - numpy
       run:
           - numpy

``ignore_version`` is an empty list by default. The actual build performed is
probably done with the last 'numpy' list element in the variant, but that's
an implementation detail that you should not depend on. The order is
considered unspecified behavior, because the output should be independent of the
input versions. If the output is not independent of input versions, don't use
this key!

Any pinning done in the run requirements will affect the hash, and thus builds
will be done for each variant in the matrix. Any package that sometimes is used
for its compiled interface and sometimes used for only its python interface may
benefit from careful use of ``ignore_version`` in the latter case.

Note: ``pin_run_as_build`` is kind of the opposite of ``ignore_version``. Where
they conflict, ``pin_run_as_build`` takes priority.


.. _CLI_vars:

CONDA_* variables and command line arguments to conda-build
-----------------------------------------------------------

To ensure consistency with existing users of conda-build, environment variables
such as CONDA_PY behave as they always have, and they overwrite all variants set
in files or passed to the API.

The full list of respected environment variables are:

* CONDA_PY
* CONDA_NPY
* CONDA_R
* CONDA_PERL
* CONDA_LUA

CLI flags are also still available. These are sticking around for their
usefulness in one-off jobs.

* --python
* --numpy
* --R
* --perl
* --lua

In addition to these traditional options, there's one new flag to specify
variants: ``--variants``. This flag accepts a string of JSON-formatted text. For
example:

.. code-block:: shell

    conda build recipe --variants "{python: [2.7, 3.5], vc: [9, 14]}"


Aggregation of multiple variants
--------------------------------

The matrix of all variants is first consolidated from several dicts of lists
into a single dict of lists, and then transformed in a list of dicts (using the
Cartesian product of lists), where each value is a single string from the list
of potential values.

For example, general input for ``variants`` could be something like:

.. code-block:: python

    a = {'python': ['2.7', '3.5'], 'numpy': ['1.10', '1.11']}
    # values can be strings or lists.  Strings are converted to one-element lists internally.
    b = {'python': ['3.4', '3.5'], 'numpy': '1.11'}

Here, let's say ``b`` is found after ``a``, and thus has priority over ``a``. Merging these
two variants yields:

.. code-block:: python

    merged = {'python': ['3.4', '3.5'], 'numpy': ['1.11']}

``b``'s values for ``python`` have overwritten ``a``'s. From here, we compute the
Cartesian product of all input variables. The end result is a collection of
dicts, each with a string for each value. Output would be something like:

.. code-block:: python

    variants = [{'python': '3.4', 'numpy': '1.11'}, {'python': '3.5', 'numpy': '1.11'}]

conda-build would loop over these variants where appropriate, such as when
building, outputting package output names, and so on.

If ``numpy`` had had two values instead of one, we'd end up with *four* output
variants: 2 variants for ``python``, *times* two variants for ``numpy``:

.. code-block:: python

    variants = [{'python': '3.4', 'numpy': '1.11'}, {'python': '3.5', 'numpy': '1.11'},
                {'python': '3.4', 'numpy': '1.10'}, {'python': '3.5', 'numpy': '1.10'}]


Bootstrapping pins based on an existing environment
---------------------------------------------------

To establish your initial variant, you may point at an existing conda
environment. Conda-build will examine the contents of that environment and pin
to the exact requirements that make up that environment.

.. code-block:: shell

   conda build --bootstrap name_of_env

You may specify either environment name or filesystem path to the environment.
Note that specifying environment name does mean depending on conda's
environment lookup.


Extended keys
-------------

These are not looped over to establish the build matrix. Rather, they are
aggregated from all input variants, and each derived variant shares the whole
set. These are used internally for tracking which requirements should be pinned,
for example, with the ``pin_run_as_build`` key. You can add your own extended
keys by passing in values for the ``extend_keys`` key for any variant.

For example, if you wanted to collect some aggregate trait from multiple
conda_build_config.yaml files, you could do something like this:

HOME/conda_build_config.yaml:

.. code-block:: yaml

   some_trait:
     - dog
   extend_keys:
     - some_trait

recipe/conda_build_config.yaml:

.. code-block:: yaml

   some_trait:
     - pony
   extend_keys:
     - some_trait

Note that *both* of the conda_build_config.yaml files need to list the trait as
an ``extend_keys`` entry.  If you list it in only one of them, an error will be
raised, to avoid confusion with one conda_build_config.yaml file that would add
entries to the build matrix, and another which would not. For example, this
should raise an error:

.. code-block:: yaml

   some_trait:
     - dog

recipe/conda_build_config.yaml:

.. code-block:: yaml

   some_trait:
     - pony
   extend_keys:
     - some_trait

When our two proper yaml config files are combined, ordinarily the recipe-local
variant would overwrite the user-wide variant, yielding ``{'some_trait':
'pony'}``. However, with the extend_keys entry, we end up with what we've always
wanted: a dog *and* pony show: ``{'some_trait': ['dog', 'pony'])}``

Again, mostly an internal implementation detail - unless you find a use for it.
Internally, it is used to aggregate the ``pin_run_as_build`` and
``ignore_version`` entries from any of your conda_build_config.yaml
files.


Customizing compatibility
-------------------------

.. _pinning_expressions:

Pinning expressions
~~~~~~~~~~~~~~~~~~~

Pinning expressions are the syntax used to specify how many parts of the version
to pin. They are by convention strings containing ``x`` characters separated by
``.``. The number of version parts to pin is simply the number of things that
are separated by ``.``. For example, ``"x.x"`` pins major and minor version.
``"x"`` pins only major version.

Wherever pinning expressions are accepted, you can customize both lower and
upper bounds.

.. code-block:: python

    # produces pins like >=1.11.2,<1.12
    variants = [{'numpy': '1.11', 'pin_run_as_build': {'numpy': {'max_pin': 'x.x'}}}]

Note that the final pin may be more specific than your initial spec. Here, the
spec is 1.11, but the produced pin could be 1.11.2, the exact version of numpy
that was used at build time.

.. code-block:: python

    # produces pins like >=1.11,<2
    variants = [{'numpy': '1.11', 'pin_run_as_build': {'numpy': {'min_pin': 'x.x', 'max_pin': 'x'}}}]


Pinning at the variant level
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Some packages, such as boost, *always* need to be pinned at runtime to the
version that was present at build time. For these cases where the need for
pinning is consistent, pinning at the variant level is a good option.
Conda-build will automatically pin run requirements to the versions present in
the build environment when the following conditions are met:

1. The dependency is listed in the requirements/build section. It can be pinned,
   but does not need to be.
2. The dependency is listed by name (no pinning) in the requirements/run section.
3. The ``pin_run_as_build`` key in the variant has a value that is a dictionary,
   containing a key that matches the dependency name listed in the run
   requirements. The value should be a dictionary with up to 4 keys:
   ``min_pin``, ``max_pin``, ``lower_bound``, ``upper_bound``. The first two are
   pinning expressions. The latter two are version numbers, overriding detection
   of current version.

An example variant/recipe is shown here:

conda_build_config.yaml:

.. code-block:: yaml

    boost: 1.63
    pin_run_as_build:
        boost:
          max_pin: x.x

meta.yaml:

.. code-block:: yaml

   requirements:
       build:
           - boost {{ boost }}
       run:
           - boost

The result here is that the runtime boost dependency will be pinned to
``>=(current boost 1.63.x version),<1.64``.

More details on the ``pin_run_as_build`` function is below in the
:ref:`extra_jinja2` section.

Note that there are some packages that you should not use ``pin_run_as_build``
for. Packages that don't *always* need to be pinned should be pinned on a
per-recipe basis (described in the next section). Numpy is an interesting
example here. It actually would not make a good case for pinning at the variant
level. Because you only need this kind of pinning for recipes that use Numpy's C
API, it would actually be better not to pin numpy with ``pin_run_as_build``.
Pinning it is over-constraining your requirements unnecessarily when you are not
using Numpy's C API. Instead, we should customize it for each recipe that uses
numpy.  See also the `Avoiding unnecessary builds`_ section above.


Pinning at the recipe level
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pinning at the recipe level overrides pinning at the variant level, because run
dependencies that have pinning values in meta.yaml (even as jinja variables) are
ignored by the logic handling ``pin_run_as_build``. We expect that pinning at
the recipe level will be used when some recipe's pinning is unusually stringent
(or loose) relative to some standard pinning from the variant level.

By default, with the ``pin_compatible('package_name')`` function, conda-build pins to your
current version and less than the next major version. For projects that don't
follow the philosophy of semantic versioning, you might want to restrict things
more tightly. To do so, you can pass one of two arguments to the pin_compatible
function.

.. code-block:: python

    variants = [{'numpy': '1.11'}]

meta.yaml:

.. code-block:: yaml

   requirements:
       build:
           - numpy {{ numpy }}
       run:
           - {{ pin_compatible('numpy', max_pin='x.x') }}


This would yield a pinning of ``>=1.11.2,<1.12``

The syntax for the ``min_pin`` and ``max_pin`` is a string pinning expression.
Each can be passed independently of the other. An example of specifying both:


.. code-block:: python

    variants = [{'numpy': '1.11'}]

meta.yaml:

.. code-block:: yaml

   requirements:
       build:
           - numpy {{ numpy }}
       run:
           - {{ pin_compatible('numpy', min_pin='x.x', max_pin='x.x') }}


This would yield a pinning of ``>=1.11,<1.12``


You can also pass the minimum or maximum version directly. These arguments supersede the
``min_pin`` and ``max_pin`` arguments and are thus mutually exclusive.


.. code-block:: python

    variants = [{'numpy': '1.11'}]

meta.yaml:

.. code-block:: yaml

   requirements:
       build:
           - numpy {{ numpy }}
       run:
           - {{ pin_compatible('numpy', lower_bound='1.10', upper_bound='3.0') }}


This would yield a pinning of ``>=1.10,<3.0``


Appending to recipes
--------------------

As of conda-build 3.0, you can add a file named ``recipe_append.yaml`` in the
same folder as your ``meta.yaml`` file. This file is considered to follow the
same rules as meta.yaml, except that selectors and Jinja2 templates are not
evaluated. Evaluation of selectors and Jinja2 templates will likely be added
in future development.

Any contents in ``recipe_append.yaml`` will add to the contents of meta.yaml.
List values will be extended, and string values will be concatenated. The
proposed use case for this is to tweak/extend central recipes, such as those
from conda-forge, with additional requirements while minimizing the actual
changes to recipe files, so as to avoid merge conflicts and source code
divergence.


Partially clobbering recipes
----------------------------

As of conda-build 3.0, you can add a file named ``recipe_clobber.yaml`` in the
same folder as your ``meta.yaml`` file. This file is considered to follow the
same rules as meta.yaml, except that selectors and Jinja2 templates are not
evaluated. Evaluation of selectors and Jinja2 templates will likely be added
in future development.

Any contents in ``recipe_clobber.yaml`` will replace the contents of meta.yaml.
This can be useful, for example, for replacing the source URL without copying
the rest of the recipe into a fork.


Differentiating packages built with different variants
------------------------------------------------------

With only a few things supported, we could just add things to the filename, such
as py27 for python, or np111 for numpy. Variants are meant to support the
general case, and in the general case this is no longer an option. Instead,
part of the recipe is hashed using the sha1 algorithm, and that hash is a
unique identifier. The information that went into the hash is stored with the
package, in a file at ``info/hash_input.json``. Currently, only the first 7
characters of the hash are stored. Output package names will keep the pyXY and
npXYY for now, but have added the 7-character hash. Your package names will
look like:

``my-package-1.0-py27h3142afe_0.tar.bz2``

Since conflicts only need to be prevented within one version of a package, we
think this will be adequate. If you run into hash collisions with this limited
subspace, please file an issue on the `conda-build issue tracker
<https://github.com/conda/conda-build/issues>`_.

The information that goes into this hash is currently defined in conda-build's
metadata.py module, in the _get_hash_contents member function. This function
captures the following information:

* ``source`` section
* ``requirements`` section
* ``build`` section, except:
  * ``number``
  * ``string``
* any other recipe files in the folder with meta.yaml, such as bld.bat,
  build.sh, etc. Every file other than meta.yaml is part of the hash.

All "falsey" values such as empty list values are removed.

There is a CLI tool that just pretty-prints this json file for easy viewing:

.. code-block:: shell

   conda inspect hash-inputs <package path>

This produces output such as:

.. code-block:: shell

   {'test_rm_rf_does_not_follow_links-1.0-h7330_0': {u'build': {u'script': u'python setup.py install --single-version-externally-managed --record=record.txt'},
                                                  u'requirements': {u'build': [u'openssl 1.0.2k 0',
                                                                               u'pip 9.0.1 py27_1',
                                                                               u'python 2.7.13 0',
                                                                               u'readline 6.2 2',
                                                                               u'setuptools 27.2.0 py27_0',
                                                                               u'sqlite 3.13.0 1',
                                                                               u'tk 8.5.18 0',
                                                                               u'wheel 0.29.0 py27_0',
                                                                               u'zlib 1.2.8 3']},
                                                  u'source': {u'path': u'/Users/msarahan/code/conda-build/tests/test-recipes/split-packages/_rm_rf_stays_within_prefix'}}}


.. _extra_jinja2:

Extra Jinja2 functions
----------------------

Two especially common operations when dealing with these API and ABI
incompatibilities are ways of specifying such compatibility, and of explicitly
expressing the compiler to be used. Three new Jinja2 functions are available when
evaluating ``meta.yaml`` templates:

* ``pin_compatible('package_name', min_pin='x.x.x.x.x.x', max_pin='x',
  lower_bound=None, upper_bound=None)``: To be used as pin in run and/or test
  requirements. Takes package name argument. Looks up compatibility of named
  package installed in the build environment, and writes compatible range pin
  for run and/or test requirements. Defaults to a semver-based assumption:
  ``package_name >=(current version),<(next major version)``. Pass ``min_pin``
  or ``max_pin`` a `Pinning expressions`_ . This will be enhanced as time goes
  on with information from `ABI Laboratory <https://abi-laboratory.pro/>`_.

* ``pin_subpackage('package_name', min_pin='x.x.x.x.x.x', max_pin='x',
  exact=False)``: To be used as pin in run and/or test requirements. Takes
  package name argument. Used to refer to particular versions of subpackages
  built by parent recipe as dependencies elsewhere in that recipe. Can use
  either pinning expressions, or exact (including build string).

* ``compiler('language')``: To be used in build requirements most commonly.
  Run or test as necessary. Takes language name argument. This is shorthand to
  facilitate cross compiler usage. This Jinja2 function ties together two
  variant variables, ``{language}_compiler`` and ``target_platform``, and
  outputs a single compiler package name. For example, this could be used to
  compile outputs targeting x86_64 and arm in one recipe, with a variant.

There are default "native" compilers that are used when no compiler is specified
in any variant. These are defined in `conda-build's jinja_context.py file
<https://github.com/conda/conda-build/blob/master/conda_build/jinja_context.py>`_.
Most of the time, users will not need to provide compilers in their variants -
just leave them empty, and conda-build will use the defaults appropriate for
your system.


.. _referencing_subpackages:

Referencing subpackages
-----------------------

Conda-build 2.1 brought in the ability to build multiple output packages from a
single recipe. This is useful in cases where you have a big build that outputs a
lot of things at once, but those things really belong in their own packages. For
example, building gcc outputs not only gcc, but also gfortran, g++, and runtime
libraries for gcc, gfotran and g++. Each of those should be their own package to
make things as clean as possible. Unfortunately, if there are separate recipes
to repack the different pieces from a larger whole package, it can be hard to
keep them in sync. That's where variants come in. Variants, and more
specifically the ``pin_subpackage(name)`` function, give you a way to refer to
the subpackage with control over how tightly the subpackage version relationship
should be in relation to other subpackages or the parent package.

meta.yaml:

.. code-block:: yaml

   package:
     name: subpackage_demo
     version: 1.0

   requirements:
     run:
       - {{ pin_subpackage('subpackage_1') }}
       - {{ pin_subpackage('subpackage_2', max_pin='x.x') }}
       - {{ pin_subpackage('subpackage_3', min_pin='x.x', max_pin='x.x') }}
       - {{ pin_subpackage('subpackage_4', exact=True) }}


   outputs:
     - name: subpackage_1
       version: 1.0.0
     - name: subpackage_2
       version: 2.0.0
     - name: subpackage_3
       version: 3.0.0
     - name: subpackage_4
       version: 4.0.0

Here, the parent package will have the following different runtime dependencies:

* subpackage_1 >=1.0.0,<2 (default uses ``min_pin='x.x.x.x.x.x``,
  ``max_pin='x'``, pins to major version with default >= current version lower
  bound)
* subpackage_2 >=2.0.0,<2.1 (more stringent upper bound)
* subpackage_3 >=3.0,<3.1 (less stringent lower bound, more stringent upper bound)
* subpackage_4 4.0.0 h81241af (exact pinning - version plus build string)


Compiler packages
-----------------

On Mac and Linux, we can and do ship gcc packages.  These will become even more
powerful with variants, since you can specify versions of your compiler much
more explicitly, and build against different versions, or with different flags
set in the compiler package's activate.d scripts. On Windows, rather than
providing the actual compilers in packages, we still use the compilers that
are installed on the system. The analogous compiler packages on Windows run
any compiler activation scripts and set compiler flags instead of actually
installing anything.

Over time, conda-build will require that all packages explicitly list their
compiler requirements this way. This is to both simplify conda-build and improve
the tracking of metadata associated with compilers - localize it to compiler
packages, even if those packages are doing nothing more than activating an
already-installed compiler, such as Visual Studio.

Note also the ``run_exports`` key in meta.yaml. This is useful for compiler
recipes to impose runtime constraints based on the versions of subpackages
created by the compiler recipe. For more information, see the :ref:`run_exports`
section of the meta.yaml docs. Compiler packages provided by Anaconda use the
run_exports key extensively. For example, recipes that include the
``gcc_linux-cos5-x86_64`` package as a build time dependency (either directly,
or through a ``{{ compilers('c') }}`` jinja2 function) will automatically have a
compatible libgcc runtime dependency added.


Cross-compiling
---------------

The compiler jinja2 function is written to support cross-compilers. This depends
on setting at least two variant keys: ``(language)_compiler`` and
``target_platform``. The target platform is appended to the value of
``(language)_compiler`` with the ``_`` character. This leads to package names
like ``g++_linux-aarch64``. We recommend a convention for naming your
compiler packages as: ``<compiler name>_<target_platform>``

Using a cross-compiler in a recipe would look like the following:

.. code-block:: python

   variants = {'cxx_compiler': ['g++'], 'target_platform': ['linux-cos5-x86_64', 'linux-aarch64']}

and a meta.yaml file:

.. code-block:: yaml

   package:
       name: compiled-code
       version: 1.0

   requirements:
       build:
           - {{ compiler('cxx') }}


This assumes that you have created two compiler packages named
``g++_linux-cos5-x86_64`` and ``g++_linux-aarch64`` - all conda-build
is providing you with is a way to loop over appropriately named cross-compiler
toolchains.


Self-consistent package ecosystems
----------------------------------

The compiler function is also how you could support a non-standard Visual Studio
version, such as using VS 2015 to compile Python 2.7 and packages for Python
2.7. To accomplish this, you need to add the ``{{ compiler('<language>') }}`` to
each recipe that will make up the system.  Environment consistency is maintained
through dependencies - thus it is useful to have the runtime be a versioned
package, with only one version being able to be installed at a time. For
example, the ``vc`` package, originally created by Conda-Forge, is a versioned
package (only one version can be installed at a time), and it installs the
correct runtime package. When the compiler package imposes such a runtime
dependency, then the resultant ecosystem is self-consistent.

Given these guidelines, consider a system of recipes using a variant like this:

.. code-block:: python

   variants = {'cxx_compiler': ['vs2015']}

The recipes include a compiler meta.yaml like this:

.. code-block:: yaml

   package:
       name: vs2015
       version: 14.0
   build:
       run_exports:
           - vc 14

They also include some compiler-using meta.yaml contents like this:

.. code-block:: yaml

   package:
       name: compiled-code
       version: 1.0

   requirements:
       build:
           # these are the same (and thus redundant) on windows, but different elsewhere
           - {{ compiler('c') }}
           - {{ compiler('cxx') }}


These recipes will create a system of packages that are all built with the
VS 2015 compiler, and which have the vc package matched at version 14, rather
than whatever default is associated with the python version.
