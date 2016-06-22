=================================================
Building conda packages for general code projects
=================================================

Overview
--------
Conda packages can be built from projects written in any language. This tutorial
will show you how to write a recipe for the ``postgis`` package. At the end you
will build the package, upload it to `anaconda.org <http://anaconda.org/>`_ and
install the package through conda.

Who is this for?
----------------
This tutorial is designed for Linux and Mac users who wish to make conda packages
for source code projects in languages other than Python. The user should already know
how to configure, compile and install C/C++ packages.

Conda build summary
~~~~~~~~~~~~~~~~~~~

Building a conda package from a general source code package can be done in four steps.

#. :ref:`before-you-start3`
#. :ref:`depends`
#. :ref:`conda-recipe`
#. :ref:`build-script`
#. :ref:`build-postgis`
#. :ref:`install`
#. :ref:`help3`

.. _before-you-start3:

Before you start
----------------

You should already have installed Miniconda_ or Anaconda_.

.. _Miniconda: http://conda.pydata.org/docs/install/quick.html
.. _Anaconda: https://docs.continuum.io/anaconda/install

Install conda-build:

.. code-block:: bash

    conda install conda-build

It is recommended that you use the latest versions of conda and conda-build. To upgrade both packages run:

.. code-block:: bash

    conda upgrade conda
    conda upgrade conda-build

Now you are ready to start building your own conda packages.

.. _depends:

Dependencies
------------
When creating conda recipes the most important aspect is to correctly list the
dependencies.

The README.postgis_ file states that the following packages are required along with the
minimum required version.

.. _README.postgis: https://github.com/postgis/postgis/blob/2.2.2/README.postgis

.. code-block:: bash

    postgresql version 9.1
    proj4 version 4.0.6
    geos version 3.4
    libxml2 version 2.5
    json-c version 0.9
    gdal version 1.9

There must exist a conda package for each of these dependencies that is available for install using conda-install.
This is because conda-build will create a private environment from which the source code for
``postgis`` will be installed and conda must install all required dependencies into that environment.

We begin by searching for each of these packages using conda-search. The only package that cannot
be found in the default channel is ``json-c``. To install this package you will have to add the
``jlaura`` channel using the conda-config command.

.. code-block:: bash

    conda config --add channels jlaura

Now that you have identified that all of the dependent packages can be installed the next step
is to write the conda recipe.

.. _conda-recipe:

Conda recipe
------------
The first step is to create a directory to store conda recipe files.

.. code-block:: bash

    mkdir postgis
    cd postgis

The conda recipe has three main components, the package name and version, the location of the source code
and the dependent packages that are required to build and run the package being built.

There are a number of ways to specify the location of the source code in a conda recipe.
Here we are going to provide the path to the Github repository and the specific revision tag
we wish to use.

NOTE: Not all Github repositories make use of revision tags. In some cases the most recent
commit is suitable.

Open a text editor and write the following to a file called meta.yaml inside the postgis directory.

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
       - geos
       - proj4
       - json-c
       - libxml2
       - postgresql >=9.1
     run:
       - gdal
       - geos
       - proj4
       - json-c
       - libxml2
       - postgresql >=9.1

    about:
      home: http://postgis.net
      license: GPL2


NOTE: Conda-build will build the package in an isolated environment, which is created from the
packages specified as build dependencies. Installing the packages into your
own working environment does not affect conda-build at all.

.. _build-script:

Build script
------------

The final step in preparing the conda build recipe is to write the build script. Since ``postgis`` is
being build for Linux and Mac we are only going to write a build.sh file in the postgis directory.

The build script file contains all of the commands required to configure, build and install the source
project. This script must run without user intervention.

By Looking at the `postgis compilation documentation <http://postgis.net/docs/manual-2.2/postgis_installation.html#installation_configuration>`_
you can see that several flags need to be provided to the configure command to indicate the location of the
dependent packages.

During execution of the conda-build command the ``$PREFIX`` environment variable is used to refer to the install path
of conda packages.  We will use ``$PREFIX`` to inform the configure command of the location of the dependent packages
listed in the build and run requirements of the conda recipe.

In a text editor make a new file called build.sh with the following content in the postgis directory.

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

NOTE: without references to the ``$PREFIX`` environment variable the configure command would look in the default
system directories for required packages and even if the package were to build correctly there is no guarantee
that other users could install the compiled conda package correctly.

NOTE: You will have to install a C/C++ compiler, autoconf and automake in order to run conda-build on this recipe.
These packages must be installed at the system level and not through conda.

.. _build-postgis:

Build the package
-----------------
Now that the recipe is complete you can build the conda package with the conda-build command from within the postgis
directory.

.. code-block:: bash

    conda build .

The start of the conda-build output should read

.. code-block:: text

    Removing old build environment
    Removing old work directory
    BUILD START: postgis-2.2.2-0
    Using Anaconda Cloud api site https://api.anaconda.org
    Fetching package metadata: ..........
    Solving package specifications: .........

If conda-build was able to successfully install the dependent packages and compile the source code conda-build
should terminate with the following message.

Mac users:

.. code-block:: text

    BUILD END: postgis-2.2.2-0
    Nothing to test for: postgis-2.2.2-0
    # If you want to upload this package to anaconda.org later, type:
    #
    # $ anaconda upload /Users/adefusco/Applications/anaconda3/conda-bld/osx-64/postgis-2.2.2-0.tar.bz2
    #
    # To have conda build upload to anaconda.org automatically, use
    # $ conda config --set anaconda_upload yes

Linux users:

.. code-block:: text

    BUILD END: postgis-2.2.2-0
    Nothing to test for: postgis-2.2.2-0
    # If you want to upload this package to anaconda.org later, type:
    #
    # $ anaconda upload /home/adefusco/anaconda3/conda-bld/linux-64/postgis-2.2.2-0.tar.bz2
    #
    # To have conda build upload to anaconda.org automatically, use
    # $ conda config --set anaconda_upload yes

NOTE: Your path may be different depending on the install location of Anaconda.

NOTE: See the troubleshooting section for help diagnosing conda-build errors.

NOTE: The package can only be installed on systems of the same architecture. You will have run the conda-build
command separately on Mac and Linux systems to make packages for both architectures.

.. _install:

Distribute and Install the package
----------------------------------
At this point you can install the package on your local machine by running the following command

.. code-block:: bash

    conda install postgis --use-local

Alternatively, you can upload the package to your anaconda.org_ channel by using the anaconda-upload command
displayed at the end of the conda-build output. This will make the package available to install by any user
with the following command.

.. code-block:: bash

    conda install -c CHANNEL postgis

NOTE: Change CHANNEL to your anaconda.org_ username.

.. _help3:

Troubleshooting and Additional Information
------------------------------------------
The troubleshooting_ page contains helpful hints for cases where conda-build fails.

.. _troubleshooting: http://conda.pydata.org/docs/troubleshooting.html

See the full conda recipe documentation_ and the `sample recipes <http://conda.pydata.org/docs/building/sample-recipes.html>`_ page for more options that are available in the conda recipe meta.yaml file.

.. _documentation: http://conda.pydata.org/docs/building/meta-yaml.html
