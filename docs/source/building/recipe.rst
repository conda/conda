.. _build:

===================
Conda build recipes
===================

Introduction
============

Building a conda package with conda build involves creating a conda recipe. The recipe 
is a flat directory holding metadata and the scripts needed to build the package. 
The conda package is then built from the conda recipe using the ``conda build`` command.

TIP: If you are new to building packages with conda, we recommend taking our series 
of three :doc:`build tutorials </build_tutorials>`.

Conda build requirements
========================

Conda and conda-build are required, and available from either Miniconda or Anaconda. 
Please follow the :doc:`Quick install</install/quick>` instructions.

**All platforms:** Install conda-build:

.. code-block:: bash

  conda install conda-build

OPTIONAL: If you wish to upload packages to Anaconda.org , an `Anaconda.org <http://anaconda.org>`_ 
account and client are required.

Conda recipe files overview
===========================

The files in a conda recipe are:

  * ``meta.yaml`` (metadata file)
  * ``build.sh`` (Unix build script which is executed using bash)
  * ``bld.bat`` (Windows build script which is executed using cmd)
  * ``run_test.[py,pl,sh,bat]`` (optional) test file
  * patches to the source (optional, see below)
  * other resources, which are not included in the source and cannot be generated 
    by the build scripts. Examples are icon files, readme, or build notes.

Conda-build invokes the following steps in this order:

  #. Reads the metadata.
  #. Downloads the source into a cache.
  #. Extracts the source into the *source directory*.
  #. Applies any patches.
  #. Creates a *build environment* and installs the build dependencies there.
  #. Runs the actual build script. The current working directory is the source 
     directory with environment variables set. The build script installs into 
     the build environment.
  #. Does some necessary post-processing steps: shebang, rpath, etc.
  #. Packages up all the files in the build environment that are new from step 5 
     into a conda package along with the necessary conda package metadata.
  #. Tests the new conda package: deletes the *build environment* and creates a 
     *test environment* with the package and its dependencies, and runs the test 
     scripts. This step is not run if there are no tests in the recipe.

There are example recipes for many conda packages in the `conda-recipes
<https://github.com/continuumio/conda-recipes>`_ repo.

NOTE: All recipe files, including meta.yaml and build scripts, are included in 
the final package archive which is distributed to users, so be careful not to 
put passwords or other sensitive information into recipes where it could leak to 
the public.

The :ref:`conda skeleton <skeleton_ref>` command can help to make skeleton
recipes for common repositories, such as `PyPI <https://pypi.python.org/pypi>`_.

More information about meta.yaml
================================

Next, please continue on to learn more about :doc:`the meta.yaml file<meta-yaml>`.
