==================================
Building conda packages on Windows
==================================

.. contents:: Contents
   :depth: 2

Overview
--------

This tutorial explains how to use conda build to create conda packages on the
Windows operating system, using the examples of SEP and pySLALIB.

On `Anaconda Cloud <https://anaconda.org>`_ you can find the final built
packages from this tutorial for both
`SEP <https://anaconda.org/wwarner/sep/files>`_ and
`pySLALIB <https://anaconda.org/wwarner/pyslalib/files>`_.

Writing the recipes will also be discussed in this tutorial. 
You can see the final `SEP recipe
<https://github.com/conda/conda-docs/tree/master/docs/source/build_tutorials/sep>`_
and the `pySLALIB recipe
<https://github.com/conda/conda-docs/tree/master/docs/source/build_tutorials/pyslalib>`_
on GitHub in the `conda documentation repository <https://github.com/conda/conda-docs>`_.


Before you start
----------------

You should already have installed :doc:`Miniconda <../install/quick>` or
`Anaconda <https://docs.continuum.io/anaconda/install>`_.

Install conda-build:

.. code-block:: bash

    conda install conda-build

It is recommended that you use the latest versions of conda and 
conda-build. To upgrade both packages run:

.. code-block:: bash

    conda upgrade conda
    conda upgrade conda-build

Now you are ready to start building your own conda packages on Windows.

The toolkit
-----------

Microsoft Visual Studio
~~~~~~~~~~~~~~~~~~~~~~~

In the standard practices of the conda developers, conda packages for different
versions of Python are each built with their own version of Visual Studio (VS):

* **Python 2.7** packages with Visual Studio 2008
* **Python 3.4** packages with VS 2010
* **Python 3.5** packages with VS 2015 

Using these versions of VS to build packages for each of these versions of 
Python is also the practice used for the official python.org builds of Python. 
Currently VS 2008 and VS 2010 are available only through resellers, while 
VS 2015 can be purchased online from Microsoft. 

Alternatives to Microsoft Visual Studio
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There are free alternatives available for each version of the VS 
compilers.

Instead of VS 2008, it is often possible to substitute the `free Microsoft
Visual C++ Compiler for Python 2.7
<https://www.microsoft.com/en-us/download/details.aspx?id=44266>`_.

Instead of VS 2010, it is often possible to substitute the `free
Microsoft Windows SDK for Windows 7 and .NET Framework 4
<https://www.microsoft.com/en-us/download/details.aspx?id=8279>`_.

Make sure that you also install `VS 2010 Service Pack 1 (SP1)
<https://www.microsoft.com/en-us/download/details.aspx?id=23691>`_.
 
Due to a bug in the VS 2010 SP1 installer, the compiler tools may be removed
during installation of VS 2010 SP1. They can be restored as described at
https://www.microsoft.com/en-us/download/details.aspx?id=4422 .

Visual Studio 2015 has a `full featured free Community edition
<https://www.visualstudio.com/en-us/products/visual-studio-community-vs.aspx>`_
for academic research, open source projects, and certain other
use cases.

The MS Visual C++ Compiler for Python 2.7 and the Microsoft Windows 
SDK for Windows 7 and .NET Framework 4 are both reasonably well 
tested. Conda build is carefully tested to support these configurations, 
but there are known issues with the CMake build tool and these free VS 
2008 and 2010 alternatives. In these case, you should prefer the 
"NMake Makefile" generator, rather than a Visual Studio solution 
generator.

Windows versions
~~~~~~~~~~~~~~~~

Any recent version of Windows may be used. These examples were 
built on Windows 8.1.

Other tools needed
~~~~~~~~~~~~~~~~~~

Some environments initially lack tools such as bzip2 or Git 
that may be needed for some build workflows.

Git is available through conda: ``conda install git``

bzip2 can be obtained and installed the same way. The conda bzip2 
package includes only the bzip2 library and not the bzip2 executable, 
so some users may need to install the bzip2 executable from another 
source such as http://gnuwin32.sourceforge.net/packages/bzip2.htm .
This executable should be placed somewhere on PATH. One good option 
is to place it in your Miniconda/Anaconda install path, in the 
Library/bin folder.

Build strategy
--------------

Conda recipes are typically built with a trial-and-error method. 
Often the first attempt to build a package will fail with compiler 
or linker errors, often caused by missing dependencies. The person 
writing the recipe will then examine these errors and modify the 
recipe to include the missing dependencies, usually as part of the 
meta.yaml file. Then the recipe writer will attempt the build again, 
and after a few of these cycles of trial and error, the package will 
be built successfully. 

Building with a Python version different from your Miniconda installation
-------------------------------------------------------------------------

Miniconda2 and Miniconda3 can each build packages for either 
Python 2 or Python 3 simply by specifying the version you want.

Miniconda2 includes only Python 2, and Miniconda3 includes only Python 3.
Installing only one makes it easier to keep track of the builds, but it is
possible to have both installed on the same system at the same time. If you do
have both installed, check to see which version comes first on PATH since
this is the one you will be using.

The "where" command is useful to check this: ``where python``

To build a package for a Python version other than the one in 
your Miniconda installation, use the ``--python`` option in the 
conda build command.

EXAMPLE: To build a Python 3.5 package with Miniconda2::

    conda build recipeDirectory --python=3.5

NOTE: Replace "recipeDirectory" with the name and path of your recipe 
directory.

Automated testing
-----------------

After the build, if the recipe directory contains a test file named 
run_test.bat (Windows) or run_test.py (any platform), the file 
runs to test the package, and any errors are reported. 
(On OS X and Linux a file named run_test.sh may be placed in the 
recipe directory.)

NOTE: Data files can be stored in the recipe directory and moved 
into the test directory when the test is run using the "files" 
section of :ref:`the "test" section of the meta.yaml file <meta-test>`.

Building the SEP package with conda and Python 3 on Windows
-----------------------------------------------------------

If you have not already, **Install Visual Studio 2015**. Choose "Custom" install
and choose to install "Visual C++" under "Programming Languages".

The `SEP documentation <https://sep.readthedocs.io>`_ states that SEP works on
Python 2 and 3 and depends only on NumPy. Searching for SEP and PyPI shows that
there is already `a PyPI package for SEP <https://pypi.python.org/pypi/sep>`_.

Because a PyPI package for SEP already exists, the ``conda 
skeleton`` command can make a skeleton or outline of a conda 
recipe based on the PyPI package. Then the recipe outline can 
be completed manually, and then conda can build a conda package 
from the completed recipe.

Make a conda skeleton recipe.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run the skeleton command::

    conda skeleton pypi sep

The skeleton installs in a newly created directory "sep". Go to that directory
to view the files::

    cd sep

Edit the skeleton files.
~~~~~~~~~~~~~~~~~~~~~~~~

Three skeleton files have been created in the directory: 

* **bld.bat** for Windows
* **build.sh** for OS X/Linux
* **meta.yaml** for all platforms. 

For this package bld.bat and build.sh need no changes. We will  
edit the meta.yaml file to add the dependency on NumPy, 
and add an optional test for the built package by 
importing it.

In the meta.yaml file, requirements section, add a line to add 
NumPy as a requirement to build the package, and a second line 
to list NumPy as a requirement to run the package. Set the NumPy 
version to the letters "x.x". Check to be sure this new line is 
aligned with "- python" on the line above it.

EXAMPLE: 

.. code-block:: yaml

    requirements:
      build:
        - python
        - numpy     x.x
    
      run:
        - python
        - numpy     x.x

NOTE: Using the letters "x.x" instead of a specific version 
such as "1.11" pins NumPy dynamically, so that the actual version 
of NumPy will be taken from the build command. Currently NumPy 
is the only package that can be pinned dynamically. Pinning is 
important for SEP because this package uses NumPy's C API through 
Cython. That API changes between NumPy versions, so it is important 
to use the same NumPy version at runtime that was used at build time.

Optional test for the built package: This will test the package at the end of
the build by making sure that the Python statement "import sep" runs
successfully. In the test section, remove the "#" used to comment out the lines 
"test:" and "imports:" and add "- sep", checking to be sure that 
the indentation is consistent with the rest of the yaml file. 

EXAMPLE:

.. code-block:: yaml

    test:
      # Python imports
      imports:
        - sep

Create a test file.
~~~~~~~~~~~~~~~~~~~

Make a new test file "run_test.py" containing this code adapted from
https://sep.readthedocs.org/en/v0.5.x/detection.html and save it to the "sep"
directory:

.. code-block:: python

    import numpy as np
    import sep
    
    data = np.random.random((256, 256))
    
    # Measure a spatially variable background of some image data
    # (a numpy array)
    bkg = sep.Background(data)
    
    # ... or with some optional parameters
    # bkg = sep.Background(data, mask=mask, bw=64, bh=64, fw=3, fh=3)

After the build, this file will be run to test the newly built package.

Now the recipe is complete. 

Build the package.
~~~~~~~~~~~~~~~~~~

Build the package using the recipe you just created::

    conda build . --numpy=1.11

Check the output.
~~~~~~~~~~~~~~~~~

Check the output to make sure the build completed 
successfully. The output will also contain the location of the final 
package file, and a command that can be run to upload the package to 
Anaconda Cloud.

Problems, questions? As discussed in the "Build strategy" section 
above, in case of any linker or compiler errors, the recipe can be 
modified and run again. 

Building the SEP package with conda and Python 2 on Windows
-----------------------------------------------------------

If you have not already, **Install Visual Studio 2008**. Choose "Custom" install
and choose to install "X64 Compilers and Tools".

**Install Visual Studio 2008 Service Pack 1**.

The `SEP documentation <https://sep.readthedocs.io>`_ states 
that SEP runs on Python 2 and 3, and depends only on NumPy. 
Searching for SEP and PyPI shows that there is already `a PyPI 
package for SEP <https://pypi.python.org/pypi/sep>`_.

Because a PyPI package for SEP already exists, the ``conda skeleton`` 
command can make a skeleton or outline of a conda recipe based 
on the PyPI package. Then the recipe outline can be completed 
manually, and then conda can build a conda package from the 
completed recipe. 

Make a conda skeleton recipe.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run the skeleton command::

    conda skeleton pypi sep

The skeleton installs in a newly created directory "sep". 
Go to that directory to view the files::

    cd sep

Edit the skeleton files.
~~~~~~~~~~~~~~~~~~~~~~~~

Three skeleton files have been created in the directory:

* **bld.bat** for Windows
* **build.sh** for OS X/Linux
* **meta.yaml** for all platforms. 

For this package bld.bat and build.sh need no changes. We will  
edit the meta.yaml file to add the dependency on NumPy, 
and add an optional test for the built package by 
importing it.

In the meta.yaml file, requirements section, add a line to add 
NumPy as a requirement to build the package, and a second line 
to list NumPy as a requirement to run the package. Set the NumPy 
version to the letters "x.x". Check to be sure this new line is 
aligned with "- python" on the line above it.

EXAMPLE: 

.. code-block:: yaml

    requirements:
      build:
        - python
        - numpy     x.x
    
      run:
        - python
        - numpy     x.x

NOTE: Using the letters "x.x" instead of a specific version such as "1.11" 
pins NumPy dynamically, so that the actual version of NumPy will be taken 
from the build command. Currently NumPy is the only package that can be 
pinned dynamically.

Optional test for the built package: This will test the package at the end of
the build by making sure that the Python statement "import sep" runs
successfully. In the test section, remove the "#" used to comment out the lines 
"test:" and "imports:" and add "- sep", checking to be sure that 
the indentation is consistent with the rest of the yaml file. 

EXAMPLE:

.. code-block:: yaml

    test:
      # Python imports
      imports:
        - sep

Create a test file.
~~~~~~~~~~~~~~~~~~~

Make a new test file "run_test.py" containing this code adapted from
https://sep.readthedocs.org/en/v0.5.x/detection.html and save it to the "sep"
directory:

.. code-block:: python

    import numpy as np
    import sep
    
    data = np.random.random((256, 256))
    
    # Measure a spatially variable background of some image data
    # (a numpy array)
    bkg = sep.Background(data)
    
    # ... or with some optional parameters
    # bkg = sep.Background(data, mask=mask, bw=64, bh=64, fw=3, fh=3)

After the build, this file will be run to test the newly built package. 
Now the recipe is complete. 

Build the package.
~~~~~~~~~~~~~~~~~~

Build the package using the recipe you just created::

    conda build . --numpy=1.11

Check the output.
~~~~~~~~~~~~~~~~~

Check the output to make sure the build completed successfully. The output will
also contain the location of the final package file, and a command that can be
run to upload the package to Anaconda Cloud.

Problems, questions? As discussed in the "Build strategy" section 
above, in case of any linker or compiler errors, the recipe can be 
modified and run again. 

Building the pySLALIB package with conda and Python 3 on Windows
----------------------------------------------------------------

Because pySLALIB includes Fortran, building it requires a Fortran compiler. 
Because there is no PyPI package for pySLALIB, we cannot use a 
skeleton recipe generated by using ``conda skeleton``, 
and must create the recipe from scratch. The steps to build 
pySLALIB are similar to the above steps to build SEP but also include 
installing the Fortran compiler, writing meta.yaml to fetch the 
package from GitHub instead of PyPI, and applying the correct patches 
to the Fortran code.

**Install Visual Studio 2015**. Choose "Custom" install and choose 
to install "Visual C++" under "Programming Languages".

**Install Intel Parallel Studio Composer Edition**. Go to `the Intel 
Fortran Compilers page <https://software.intel.com/en-us/fortran-compilers>`_.
Choose "Try & Buy" and choose Parallel Studio Composer Edition for Windows. 
You may choose the version with Fortran only instead of the version 
with Fortran and C++. There is a free 30 day trial available. Fill out 
the form, including your email address, and Intel will email you a 
download link. Download and install "Intel Parallel Studio XE Composer 
Edition for Fortran Windows".

**Install Git**. Because the pySLALIB package sources are 
retrieved from GitHub for the build, we must install Git::

    conda install git

**Make a recipe**. You can write a recipe from scratch, or use the `recipe we wrote
<https://github.com/conda/conda-docs/tree/master/docs/source/build_tutorials/pyslalib>`_.
This recipe contains four files:

* **meta.yaml** sets the GitHub location of the pySLALIB files and how 
  the system will apply the intel_fortran_use.patch.
* **bld.bat** is a Windows batch script that ensures that the correct 
  32-bit or 64-bit libraries are linked during the build and 
  runs the build.
* **run_test.py** is a test adapted from the one in the pySLALIB GitHub 
  repository to check that the build completed successfully.
* **intel_fortran_use.patch** is a patch to the pySLALIB Fortran 
  code so that it will work with the Intel Fortran compiler.

In your home directory, create a recipe directory named "pyslalib" 
and copy in these four files.

**Build the package**. In the Apps menu under "Intel Parallel 
Studio XE 2016", open the "Compiler 16.0 Update 3 for Intel 64 
Visual Studio 2015 environment" command prompt.

Run conda build, using the correct path name of the recipe 
directory, including your correct user name. Here our example 
username is "builder":

``conda build C:\Users\builder\pyslalib``

**Check the output**. Check the output to make sure the build 
completed successfully. The output will also contain the location 
of the final package file, and a command that can be run to 
upload the package to Anaconda Cloud.

**Problems, questions**? As discussed in the "Build strategy" 
section above, in case of any linker or compiler errors, the 
recipe can be modified and run again. 

Building the pySLALIB package with conda and Python 2 on Windows
----------------------------------------------------------------

Because pySLALIB includes Fortran, building it requires a Fortran compiler. 
Because there is no PyPI package for pySLALIB, we cannot use a 
skeleton recipe generated by using ``conda skeleton``, 
and must create the recipe from scratch. The steps to build 
pySLALIB are similar to the above steps to build SEP but also include 
installing the Fortran compiler, writing meta.yaml to fetch the 
package from GitHub instead of PyPI, and applying the correct patches 
to the Fortran code.

**Install Visual Studio 2008**. Choose "Custom" install and choose to install
"X64 Compilers and Tools". Install Visual Studio 2008 Service Pack 1.

**Install Intel Parallel Studio Composer Edition**. Go to `the Intel Fortran
Compilers page <https://software.intel.com/en-us/fortran-compilers>`_. Choose
"Try & Buy" and choose Parallel Studio Composer Edition for Windows. You may
choose the version with Fortran only instead of the version with Fortran and
C++. There is a free 30 day trial available. Fill out the form, including your
email address, and Intel will email you a download link.

When you click that link and open the download page for "Intel 
Parallel Studio XE Composer Edition for Fortran Windows", select 
"Additional downloads, latest updates and prior versions." Select 
version 2013 Update 6. This is "Intel Visual Fortran Composer XE 
2013 SP1 (compiler version 14.0)", the most recent Intel Fortran 
compiler that works with Visual Studio 2008. Choose "Download Now" 
and install this version.

**Install Git**. Install git, since the pySLALIB package sources 
are retrieved from GitHub for the build::

    conda install git

**Make a recipe**. You can write a recipe from scratch, or use the `recipe we wrote
<https://github.com/conda/conda-docs/tree/master/docs/source/build_tutorials/pyslalib>`_.
This recipe contains four files:

* **meta.yaml** sets the GitHub location of the pySLALIB files and how 
  the system will apply the intel_fortran_use.patch.
* **bld.bat** is a Windows batch script that ensures that the correct 
  32-bit or 64-bit libraries are linked during the build and runs the 
  build.
* **run_test.py** is a test adapted from the one in the pySLALIB GitHub 
  repository to check that the build completed successfully.
* **intel_fortran_use.patch** is a patch to the pySLALIB Fortran code 
  so that it will work with the Intel Fortran compiler.

In your home directory, create a recipe directory named "pyslalib" 
and copy in these four files.

**Build the package**. In the Apps menu under "Intel Parallel Studio 
XE 2013", open the "Intel 64 Visual Studio 2008 mode" command prompt.

Run conda build, using the correct path name of the recipe directory, 
including your correct user name. Here our example username is "builder"::

    conda build C:\Users\builder\pyslalib

**Check the output**. Check the output to make sure the build completed 
successfully. The output will also contain the location of the final 
package file, and a command that can be run to upload the package to 
Anaconda Cloud.

Problems, questions? As discussed in the "Build strategy" section above, 
in case of any linker or compiler errors, the recipe can be modified and 
run again. 
