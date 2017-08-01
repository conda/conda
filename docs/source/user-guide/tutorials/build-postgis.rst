=================================================
Building conda packages for general code projects
=================================================

.. contents::
   :local:
   :depth: 1

You can build conda packages from projects written in any
language. This tutorial describes how to write a recipe for the
postgis package, build a package, upload it to `anaconda.org
<http://anaconda.org/>`_ and install the package through conda.


Who is this for?
=================

This tutorial is for macOS and Linux users who wish to make
conda packages for source code projects in languages other than
Python. You need to know how to configure, compile and install
C/C++ packages.


.. _before-you-start3:

Before you start
=================

Before you start, check the :doc:`prerequisites <index>`.


.. _depends:

Listing dependencies
=====================

When creating conda recipes, the most important aspect is to
correctly list the dependencies.

The README.postgis_ file states that the following packages are
required along with the minimum required version:

.. _README.postgis: https://github.com/postgis/postgis/blob/2.2.2/README.postgis

.. code-block:: bash

    postgresql version 9.1
    proj4 version 4.0.6
    geos version 3.4
    libxml2 version 2.5
    json-c version 0.9
    gdal version 1.9

For each of these dependencies you need a conda package that is
available for install using ``conda install``, because conda
build creates a private environment from which the source code
for postgis is installed and conda must install all required
dependencies into that environment.

#. Search for each of these packages using ``conda search``.

   The only package that cannot
   be found in the default channel is json-c.

#. To install json-c, add the
   ``jlaura`` channel using the ``conda config`` command:

   .. code-block:: bash

       conda config --add channels jlaura

Now that you have identified that all of the dependent packages
can be installed, the next step is to write the conda recipe.


.. _conda-recipe:

Writing a conda recipe
======================

A conda recipe has 3 main components:

* The package name and version.
* The location of the source code.
* The dependent packages that are required to build and run the
  package being built.

There are a number of ways to specify the location of the source
code in a conda recipe. In this case, you provide the path to
the Github repository and the desired revision tag.

NOTE: Not all Github repositories make use of revision tags. In
some cases the most recent commit is suitable.

#. Create a directory to store the conda recipe files:

   .. code-block:: bash

      mkdir postgis
      cd postgis

#. Open a text editor, and then write the following code to a
   file called ``meta.yaml`` inside the ``postgis`` directory:

   .. code-block:: yaml

       package:
         name: postgis
         version: "2.2.2"

       source:
         git_rev: 2.2.2
         git_url: https://github.com/postgis/postgis.git

       build:
         number: 0

       requirements:
         build:
           - gdal
           -  geos
           -  proj4
           -  json-c
           -  libxml2
           -  postgresql >=9.1
         run:
           -  gdal
           -  geos
           -  proj4
           -  json-c
           -  libxml2
           -  postgresql >=9.1

       about:
         home: http://postgis.net
         license: GPL2

NOTE: Conda build creates the package in an isolated environment,
which is created from the packages specified as build
dependencies. Installing the packages into your own working
environment does not affect conda build.


.. _build-script:

Writing a build script
=======================

The final step in preparing the conda build recipe is to write
the build script. Since postgis is being built for both macOS and
Linux, you need only a single build script file, called
``build.sh``, in the ``postgis`` directory.

The build script file contains all of the commands required to
configure, build and install the source project. This script must
run without user intervention.

The `postgis compilation documentation
<http://postgis.net/docs/manual-2.2/postgis_installation.html#installation_configuration>`_
states that several flags must be provided to the ``configure``
command to indicate the location of the dependent packages.

During execution of the ``conda-build`` command, the $PREFIX
environment variable is used to refer to the install path
of conda packages.  In this case, use $PREFIX to inform the
``configure`` command of the location of the dependent packages
listed in the build and run requirements of the conda recipe.

#. In a terminal window, navigate to the ``postgis`` directory.

#. In a text editor, create a new file called ``build.sh``
   with the following content:

   .. code-block:: bash

       sh autogen.sh
       ./configure \
         --prefix=$PREFIX \
         --with-pgconfig=$PREFIX/bin/pg_config \
         --with-gdalconfig=$PREFIX/bin/gdal-config \
         --with-xml2config=$PREFIX/bin/xml2-config \
         --with-geosconfig=$PREFIX/bin/geos-config \
         --with-projdir=$PREFIX \
         --with-jsondir=$PREFIX \
         --without-raster \
         --without-topology

       make
       make install

   NOTE: Without references to the $PREFIX environment variable,
   the ``configure`` command would look in the default system
   directories for required packages. Even if the package were
   to build correctly, there is no guarantee that other users
   could install the compiled conda package correctly.

   NOTE: To run conda build on this recipe, you need to install
   a C/C++ compiler, autoconf and automake. These packages must
   be installed at the system level and not through conda.

#. Save the file to the ``postgis`` directory.


.. _build-postgis:

Building the package
=====================

Now that the recipe is complete, build the conda package
with the ``conda-build`` command from within the ``postgis``
directory:

.. code-block:: bash

    conda-build .

The start of the ``conda-build`` output should read:

.. code-block:: text

    Removing old build environment
    Removing old work directory
    BUILD START: postgis-2.2.2-0
    Using Anaconda Cloud api site https://api.anaconda.org
    Fetching package metadata: ..........
    Solving package specifications: .........

If conda build successfully installed the dependent packages and
compiled the source code, it terminates with one of the
following messages:

* macOS:

  .. code-block:: text

      BUILD END: postgis-2.2.2-0
      Nothing to test for: postgis-2.2.2-0
      # If you want to upload this package to anaconda.org later, type:
      #
      # $ anaconda upload /Users/adefusco/Applications/anaconda3/conda-bld/osx-64/postgis-2.2.2-0.tar.bz2
      #
      # To have conda build upload to anaconda.org automatically, use
      # $ conda config --set anaconda_upload yes

* Linux:

  .. code-block:: text

      BUILD END: postgis-2.2.2-0
      Nothing to test for: postgis-2.2.2-0
      # If you want to upload this package to anaconda.org later, type:
      #
      # $ anaconda upload /home/adefusco/anaconda3/conda-bld/linux-64/postgis-2.2.2-0.tar.bz2
      #
      # To have conda build upload to anaconda.org automatically, use
      # $ conda config --set anaconda_upload yes


NOTE: Your path may be different depending on the install
location of Anaconda.

Packages can be installed only on systems of the same
architecture. You need to run the ``conda-build`` command
separately on macOS and Linux systems to make packages for both
architectures.


.. _install:

Distributing and installing the package
=======================================

#. Install the package on your local machine by running:

   .. code-block:: bash

      conda install postgis --use-local

   Alternatively, you can upload the package to your
   Anaconda.org_ channel with the ``anaconda-upload`` command,
   which is displayed at the end of the ``conda-build`` output.

#. Make the package available to install by any user with:

   .. code-block:: bash

      conda install -c CHANNEL postgis

   NOTE: Replace ``CHANNEL`` with your Anaconda.org_ user name.


More information
================

For more options that are available in the conda recipe
``meta.yaml`` file, see
:doc:`../tasks/build-packages/define-metadata` and
:doc:`../tasks/build-packages/sample-recipes`.
