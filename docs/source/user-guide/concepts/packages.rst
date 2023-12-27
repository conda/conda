========
Packages
========

.. _concept-conda-package:

What is a package?
==================

A package is a compressed tarball file (.tar.bz2) or
.conda file that contains:

* system-level libraries.
* Python or other modules.
* executable programs and other components.
* metadata under the ``info/`` directory.
* a collection of files that are installed directly into an ``install`` prefix.

Conda keeps track of the dependencies between packages and platforms.
The conda package format is identical across platforms and
operating systems.

Only files, including symbolic links, are part of a conda
package. Directories are not included. Directories are created
and removed as needed, but you cannot create an empty directory
from the tar archive directly.

.conda file format
==================

The .conda file format was introduced in conda 4.7 as a more
compact, and thus faster, alternative to a tarball.

The .conda file format consists of an outer, uncompressed
ZIP-format container, with 2 inner compressed .tar files.

For the .conda format's initial internal compression format support,
we chose Zstandard (zstd). The actual compression format used does not
matter, as long as the format is supported by libarchive. The compression
format may change in the future as more advanced compression algorithms are
developed and no change to the .conda format is necessary. Only an updated
libarchive would be required to add a new compression format to .conda files.

These compressed files can be significantly smaller than their
bzip2 equivalents. In addition, they decompress much more quickly.
.conda is the preferred file format to use where available,
although we continue to provide .tar.bz2 files in tandem.

Read more about the `introduction of the .conda file format <https://www.anaconda.com/understanding-and-improving-condas-performance/>`_.

.. note::

  In conda 4.7 and later, you cannot use package names that
  end in “.conda” as they conflict with the .conda file format
  for packages.


Using packages
==============

* You may search for packages

.. code-block:: bash

  conda search scipy


* You may install a package

.. code-block:: bash

  conda install scipy


* You may build a package after `installing conda-build <https://docs.conda.io/projects/conda-build/en/latest/index.html>`_

.. code-block:: bash

  conda build my_fun_package



Package structure
=================

.. code-block:: bash

  .
  ├── bin
  │   └── pyflakes
  ├── info
  │   ├── LICENSE.txt
  │   ├── files
  │   ├── index.json
  │   ├── paths.json
  │   └── recipe
  └── lib
      └── python3.5

* bin contains relevant binaries for the package.

* lib contains the relevant library files (eg. the .py files).

* info contains package metadata.


.. _meta-package:

Metapackages
============

When a conda package is used for metadata alone and does not contain
any files, it is referred to as a metapackage.
The metapackage may contain dependencies to several core, low-level libraries
and can contain links to software files that are
automatically downloaded when executed.
Metapackages are used to capture metadata and make complicated package
specifications simpler.


An example of a metapackage is "anaconda," which
collects together all the packages in the Anaconda installer.
The command ``conda create -n envname anaconda`` creates an
environment that exactly matches what would be created from the
Anaconda installer. You can create metapackages with the
``conda metapackage`` command. Include the name and version
in the command.

Anaconda metapackage
--------------------

The Anaconda metapackage is used in the creation of the
`Anaconda Distribution <https://docs.anaconda.com/free/anaconda/>`_
installers so that they have a set of packages associated with them.
Each installer release has a version number, which corresponds
to a particular collection of packages at specific versions.
That collection of packages at specific versions is encapsulated
in the Anaconda metapackage.

The Anaconda metapackage contains several core, low-level
libraries, including compression, encryption, linear algebra, and
some GUI libraries.

`Read more about the Anaconda metapackage and Anaconda Distribution
<https://www.anaconda.com/whats-in-a-name-clarifying-the-anaconda-metapackage/>`_.

.. _mutex-metapackages:

Mutex metapackages
------------------
A mutex metapackage is a very simple package that has a
name. It need not have any dependencies or build steps.
Mutex metapackages are frequently an "output" in a recipe
that builds some variant of another package.
Mutex metapackages function as a tool to help achieve mutual
exclusivity among packages with different names.

Let's look at some examples for how to use mutex metapackages
to build NumPy against different BLAS implementations.

Building NumPy with BLAS variants
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you build NumPy with MKL, you also need to build
SciPy, scikit-learn, and anything else using BLAS
also with MKL. It is important to ensure that these
“variants” (packages built with a particular set of options)
are installed together and never with an alternate BLAS
implementation. This is to avoid crashes, slowness, or numerical problems.
Lining up these libraries is both a build-time and an install-time concern.
We’ll show how to use metapackages to achieve this need.

Let's start with the metapackage ``blas=1.0=mkl``:
https://github.com/AnacondaRecipes/intel_repack-feedstock/blob/e699b12/recipe/meta.yaml#L108-L112

Note that ``mkl`` is a string of ``blas``.

That metapackage is automatically added as a dependency
using ``run_exports`` when someone uses the mkl-devel
package as a build-time dependency:
https://github.com/AnacondaRecipes/intel_repack-feedstock/blob/e699b12/recipe/meta.yaml#L124

By the same token, here’s the metapackage for OpenBLAS:
https://github.com/AnacondaRecipes/openblas-feedstock/blob/ae5af5e/recipe/meta.yaml#L127-L131

And the ``run_exports`` for OpenBLAS, as part of
openblas-devel:
https://github.com/AnacondaRecipes/openblas-feedstock/blob/ae5af5e/recipe/meta.yaml#L100

Fundamentally, conda’s model of mutual exclusivity relies on the package name.
OpenBLAS and MKL are obviously not the same package name, and thus are not
mutually exclusive. There’s nothing stopping conda from installing both at
once. There’s nothing stopping conda from installing NumPy with MKL and SciPy
with OpenBLAS. The metapackage is what allows us to achieve the mutual
exclusivity. It unifies the options on a single package name,
but with a different build string. Automating the addition of the
metapackage with ``run_exports`` helps ensure the library consumers
(package builders who depend on libraries) will have correct dependency
information to achieve the unified runtime library collection.

Installing NumPy with BLAS variants
***********************************

To specify which variant of NumPy that you want, you could potentially
specify the BLAS library you want::

  conda install numpy mkl

However, that doesn’t actually preclude OpenBLAS from being chosen.
Neither MKL nor its dependencies are mutually exclusive (meaning they
do not have similar names and different version/build-string).

This pathway may lead to some ambiguity and solutions with mixed BLAS,
so using the metapackage is recommended. To specify MKL-powered NumPy
in a non-ambiguous way, you can specify the mutex package (either directly
or indirectly)::

  conda install numpy “blas=*=mkl”

There is a simpler way to address this, however. For example, you may want to
try another package that has the desired mutex package as a dependency.

OpenBLAS has this with its “nomkl” package:
https://github.com/AnacondaRecipes/openblas-feedstock/blob/ae5af5e/recipe/meta.yaml#L133-L147

Nothing should use “nomkl” as a dependency. It is strictly a utility for users
to facilitate switching from MKL (which is the default) to OpenBLAS.

How did MKL become the default? The solver needs a way to prioritize some packages
over others. We achieve that with an older conda feature called track_features that originally
served a different purpose.

Track_features
**************
One of conda’s optimization goals is to minimize the number of track_features needed
to specify the desired specs. By adding track_features to one or more of the options,
conda will de-prioritize it or “weigh it down.” The lowest priority package is the one
that would cause the most track_features to be activated in the environment. The default
package among many variants is the one that would cause the least track_features to be activated.

There is a catch, though: any track_features must be unique. No two packages can provide the
same track_feature. For this reason, our standard practice is to attach track_features to
the metapackage associated with what we want to be non-default.

Take another look at the OpenBLAS recipe: https://github.com/AnacondaRecipes/openblas-feedstock/blob/ae5af5e/recipe/meta.yaml#L127-L137

This attached track_features entry is why MKL is chosen over OpenBLAS.
MKL does not have any track_features associated with it. If there are 3 options,
you would attach 0 track_features to the default, then 1 track_features for the next preferred
option, and finally 2 for the least preferred option. However, since you generally only care
about the one default, it is usually sufficient to add 1 track_feature to all options other
than the default option.

More info
*********

For reference, the Visual Studio version alignment on Windows also uses mutex metapackages.
https://github.com/AnacondaRecipes/aggregate/blob/9635228/vs2017/meta.yaml#L24


.. _noarch:

Noarch packages
===============
Noarch packages are packages that are not architecture specific
and therefore only have to be built once. Noarch packages are
either generic or Python. Noarch generic packages allow users to
distribute docs, datasets, and source code in conda packages.
Noarch Python packages are described below.

Declaring these packages as ``noarch`` in the ``build`` section of
the ``meta.yaml`` reduces shared CI resources. Therefore, all packages
that qualify to be noarch packages should be declared as such.

Noarch Python
-------------
The ``noarch: python`` directive in the build section
makes pure-Python packages that only need to be built once.

Noarch Python packages cut down on the overhead of building multiple
different pure Python packages on different architectures and Python
versions by sorting out platform and Python version-specific differences
at install time.

In order to qualify as a noarch Python package, all of the following
criteria must be fulfilled:

* No compiled extensions.

* No post-link, pre-link, or pre-unlink scripts.

* No OS-specific build scripts.

* No Python version-specific requirements.

* No skips except for Python version. If the recipe is py3 only,
  remove skip statement and add version constraint on Python in host
  and run section.

* 2to3 is not used.

* Scripts argument in setup.py is not used.

* If ``console_script`` entrypoints are in setup.py,
  they are listed in ``meta.yaml``.

* No activate scripts.

* Not a dependency of conda.

.. note::
   While ``noarch: python`` does not work with selectors, it does
   work with version constraints. ``skip: True  # [py2k]`` can sometimes
   be replaced with a constrained Python version in the host and run
   subsections, for example: ``python >=3`` instead of just ``python``.

.. note::
   Only ``console_script`` entry points have to be listed in ``meta.yaml``.
   Other entry points do not conflict with ``noarch`` and therefore do
   not require extra treatment.

Read more about `conda's noarch packages <https://www.anaconda.com/condas-new-noarch-packages/>`_.

.. _link_unlink:

Link and unlink scripts
=======================

You may optionally execute scripts before and after the link
and unlink steps. For more information, see `Adding pre-link, post-link, and pre-unlink scripts <https://docs.conda.io/projects/conda-build/en/latest/resources/link-scripts.html>`_.

.. _package_specs:

More information
================

For more information, go for a deeper dive in our :doc:`managing packages guide <../tasks/manage-pkgs>`.
Learn more about package metadata, repository structure and index,
and package match specifications at :doc:`Package specifications <../concepts/pkg-specs>`.
