==================================
Building conda packages on Windows
==================================

.. contents::
   :local:
   :depth: 2


This tutorial describes how to use conda build to create conda
packages on the Windows operating system, using the examples of
SEP and pySLALIB.

The final built packages from this tutorial are available on
`Anaconda Cloud <https://anaconda.org>`_:

* `SEP <https://anaconda.org/wwarner/sep/files>`_.

* `pySLALIB <https://anaconda.org/wwarner/pyslalib/files>`_.

This tutorial also describes writing recipes. You can see the
final `SEP recipe
<https://github.com/conda/conda-docs/tree/master/docs/source/user-guide/tutorials/sep>`_
and the `pySLALIB recipe
<https://github.com/conda/conda-docs/tree/master/docs/source/user-guide/tutorials/pyslalib>`_
on GitHub in the `conda documentation repository
<https://github.com/conda/conda-docs>`_.


Before you start
=================

Before you start, check the :doc:`prerequisites <index>`.


Toolkit
=========

Microsoft Visual Studio
------------------------

In the standard practices of the conda developers, conda packages
for different versions of Python are each built with their own
version of Visual Studio (VS):

* Python 2.7 packages with Visual Studio 2008
* Python 3.4 packages with VS 2010
* Python 3.5 packages with VS 2015
* Python 3.6 packages with VS 2015

Using these versions of VS to build packages for each of these
versions of Python is also the practice used for the official
python.org builds of Python. Currently VS 2008 and VS 2010 are
available only through resellers, while VS 2015 can be purchased
online from Microsoft.


Alternatives to Microsoft Visual Studio
----------------------------------------

There are free alternatives available for each version of the VS
compilers:

* Instead of VS 2008, it is often possible to substitute the
  `free Microsoft Visual C++ Compiler for Python 2.7
  <https://www.microsoft.com/en-us/download/details.aspx?id=44266>`_.

* Instead of VS 2010, it is often possible to substitute the
  `free Microsoft Windows SDK for Windows 7 and .NET Framework 4
  <https://www.microsoft.com/en-us/download/details.aspx?id=8279>`_.

* Make sure that you also install `VS 2010 Service Pack 1 (SP1)
  <https://www.microsoft.com/en-us/download/details.aspx?id=23691>`_.

* Due to a bug in the VS 2010 SP1 installer, the compiler tools
  may be removed during installation of VS 2010 SP1. They can be
  restored as described in `Microsoft Visual C++ 2010 Service
  Pack 1 Compiler Update for the Windows SDK 7.1
  <https://www.microsoft.com/en-us/download/details.aspx?id=4422>`_.

* Visual Studio 2015 has a `full featured free Community edition
  <https://www.visualstudio.com/en-us/products/visual-studio-community-vs.aspx>`_
  for academic research, open source projects and certain other
  use cases.


The MS Visual C++ Compiler for Python 2.7 and the Microsoft
Windows SDK for Windows 7 and .NET Framework 4 are both
reasonably well tested. Conda build is carefully tested to
support these configurations, but there are known issues with the
CMake build tool and these free VS 2008 and 2010 alternatives.
In these cases, you should prefer the "NMake Makefile" generator,
rather than a Visual Studio solution generator.


Windows versions
-----------------

You can use any recent version of Windows. These examples were
built on Windows 8.1.

Other tools
------------

Some environments initially lack tools such as bzip2 or Git
that may be needed for some build workflows.

Git is available through conda: ``conda install git``

You can obtain bzip2 the same way. The conda bzip2 package
includes only the bzip2 library and not the bzip2 executable, so
some users may need to install the bzip2 executable from another
source such as http://gnuwin32.sourceforge.net/packages/bzip2.htm.
Place this executable somewhere on PATH. One good option is to
place it in your Miniconda/Anaconda install path, in the
``Library/bin`` folder.


Developing a build strategy
============================

Conda recipes are typically built with a trial-and-error method.
Often the first attempt to build a package fails with compiler
or linker errors, often caused by missing dependencies. The person
writing the recipe then examines these errors and modifies the
recipe to include the missing dependencies, usually as part of the
``meta.yaml`` file. Then the recipe writer attempts the build
again, and after a few of these cycles of trial and error, the
package builds successfully.


Building with a Python version different from your Miniconda installation
==========================================================================

Miniconda2 and Miniconda3 can each build packages for either
Python 2 or Python 3 simply by specifying the version you want.
Miniconda2 includes only Python 2, and Miniconda3 includes only
Python 3.

Installing only one makes it easier to keep track of
the builds, but it is possible to have both installed on the same
system at the same time. If you have both installed, use the
``where`` command to see which version comes first on PATH since
this is the one you will be using::

  where python

To build a package for a Python version other than the one in
your Miniconda installation, use the ``--python`` option in the
``conda-build`` command.

EXAMPLE: To build a Python 3.5 package with Miniconda2::

    conda-build recipeDirectory --python=3.5

NOTE: Replace ``recipeDirectory`` with the name and path of your
recipe directory.


Automated testing
==================

After the build, if the recipe directory contains a test file
named ``run_test.bat`` on Windows, or ``run_test.sh`` on macOS or Linux,
or ``run_test.py`` on any platform, the file runs to test the package,
and any errors are reported.

NOTE: Use the :ref:`Test section of the meta.yaml file
<meta-test>` to move data files from the recipe directory to the
test directory when the test is run.


Building a SEP package with conda and Python 2 or 3
=====================================================

The `SEP documentation <https://sep.readthedocs.io>`_ states
that SEP runs on Python 2 and 3, and it depends only on NumPy.
Searching for SEP and PyPI shows that there is already `a PyPI
package for SEP <https://pypi.python.org/pypi/sep>`_.

Because a PyPI package for SEP already exists, the
``conda skeleton`` command can make a skeleton or outline of a
conda recipe based on the PyPI package. Then the recipe outline
can be completed manually, and conda can build a conda package
from the completed recipe.


Install Visual Studio
----------------------

If you have not already done so, install the appropriate version
of Visual Studio:

* For Python 3---Visual Studio 2015:

  #. Choose Custom install.

  #. Under Programming Languages, choose to install Visual C++ .

* For Python 2---Visual Studio 2008:

  #. Choose Custom install.

  #. Choose to install X64 Compilers and Tools. Install Service
     Pack 1.


Make a conda skeleton recipe
-----------------------------

#. Run the skeleton command::

       conda skeleton pypi sep

   The ``skeleton`` command installs into a newly created
   directory called ``sep``.

#. Go to the ``sep`` directory to view the files::

       cd sep

   Three skeleton files have been created:

   * ``bld.bat`` for Windows.
   * ``build.sh`` for macOS/Linux.
   * ``meta.yaml`` for all platforms.


Edit the skeleton files
------------------------

For this package, ``bld.bat`` and ``build.sh`` need no changes.
You need to edit the ``meta.yaml`` file to add the dependency on
NumPy and add an optional test for the built package by importing
it.

#. In the requirements section of the ``meta.yaml`` file, add a
   line that adds NumPy as a requirement to build the package.

#. Add a second line to list NumPy as a requirement to run the
   package.

Set the NumPy version to the letters ``x.x``.

Make sure the new line is aligned with ``- python`` on the
line above it.

EXAMPLE:

.. code-block:: yaml

    requirements:
      build:
        - python
        - numpy     x.x

      run:
        - python
        - numpy     x.x

NOTE: Using the letters ``x.x`` instead of a specific version
such as ``1.11`` pins NumPy dynamically, so that the actual
version of NumPy is taken from the build command. Currently NumPy
is the only package that can be pinned dynamically. Pinning is
important for SEP because this package uses NumPy's C API through
Cython. That API changes between NumPy versions, so it is
important to use the same NumPy version at runtime that was used
at build time.

Optional---Add a test for the built package
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Adding this optional test will test the package at the end of the
build by making sure that the Python statement ``import sep``
runs successfully:

#. In the test section, remove the ``#`` used to comment out the
   lines ``test:`` and ``imports:``.

#. Add ``- sep``, checking to be sure that the indentation is
   consistent with the rest of the file.

EXAMPLE:

.. code-block:: yaml

    test:
      # Python imports
      imports:
        - sep


Create a test file
-------------------

Make a new test file called ``run_test.py`` containing the
following code adapted from `Background estimation and source
detection <https://sep.readthedocs.org/en/v0.5.x/detection.html>`_,
and save it to the ``sep`` directory:

.. code-block:: python

    import numpy as np
    import sep

    data = np.random.random((256, 256))

    # Measure a spatially variable background of some image data
    # (a numpy array)
    bkg = sep.Background(data)

    # ... or with some optional parameters
    # bkg = sep.Background(data, mask=mask, bw=64, bh=64, fw=3, fh=3)


After the build, this file is run to test the newly built package.

Now the recipe is complete.


Build the package
-----------------

Build the package using the recipe you just created::

    conda-build . --numpy=1.11


Check the output
----------------

#. Check the output to make sure that the build completed
   successfully. The output contains the location of the final
   package file and a command to upload the package to Anaconda
   Cloud.

#. If there are any linker or compiler errors, modify the recipe
   and build again.


Building a pySLALIB package with conda and Python 2 or 3
=========================================================

This procedure describes how to build a package with Python 2 or
Python 3. Follow the instructions for the version that you want
to build with.

Because pySLALIB includes Fortran, building it requires a Fortran
compiler. Because there is no PyPI package for pySLALIB, you
cannot use a skeleton recipe generated by using
``conda skeleton``. You must create the recipe from scratch. The
steps to build pySLALIB are similar to the steps to build SEP,
but they also include installing the Fortran compiler, writing
``meta.yaml`` to fetch the package from GitHub instead of PyPI
and applying the correct patches to the Fortran code.

To build a pySLALIB package:

#. Install Visual Studio:

   * For Python 3, install Visual Studio 2015. Choose Custom
     install. Under Programming Languages, choose to install
     Visual C++.

   * For Python 2, install Visual Studio 2008. Choose Custom
     install. Choose to install X64 Compilers and Tools. Install
     Visual Studio 2008 Service Pack 1.

#. Install Intel Parallel Studio Composer Edition. Go to `the
   Intel Fortran Compilers page
   <https://software.intel.com/en-us/fortran-compilers>`_. Choose
   Try & Buy. Choose Parallel Studio Composer Edition for
   Windows. You may choose the version with Fortran only
   instead of the version with Fortran and C++. There is a free
   30-day trial available. Fill out the form, including your
   email address. Intel will email you a download link.

   * For Python 3, download and install Intel Parallel Studio XE
     Composer Edition for Fortran Windows.

   * For Python 2, open the download page for Intel Parallel
     Studio XE Composer Edition for Fortran Windows. Select
     Additional downloads, latest updates and prior versions.
     Select version 2013 Update 6. This is Intel Visual Fortran
     Composer XE 2013 SP1 (compiler version 14.0), the most
     recent Intel Fortran compiler that works with Visual Studio
     2008. Choose Download Now and install this version.

#. Install Git. Because the pySLALIB package sources are
   retrieved from GitHub for the build, you must install Git::

     conda install git

#. Make a recipe. You can write a recipe from scratch, or use
   the `recipe we wrote
   <https://github.com/conda/conda-docs/tree/master/docs/source/user-guide/tutorials/pyslalib>`_.
   This recipe contains 4 files:

   * ``meta.yaml`` sets the GitHub location of the pySLALIB files
     and how the system will apply the
     ``intel_fortran_use.patch``.
   * ``bld.bat`` is a Windows batch script that ensures that the
     correct 32-bit or 64-bit libraries are linked during the
     build and runs the build.
   * ``run_test.py`` is a test adapted from the one in the
     pySLALIB GitHub repository to check that the build completed
     successfully.
   * ``intel_fortran_use.patch`` is a patch to the pySLALIB
     Fortran code so that it works with the Intel Fortran
     compiler.

#. In your home directory, create a recipe directory named
   ``pyslalib`` and copy in the 4 files mentioned in the previous
   step.

#. Build the package.

   * For Python 3, in the **Apps** menu, under Intel Parallel
     Studio XE 2016, open the Compiler 16.0 Update 3 for Intel 64
     Visual Studio 2015 environment command prompt.

   * For Python 2, in the **Apps** menu, under Intel Parallel
     Studio XE 2013, open the Intel 64 Visual Studio 2008 mode command prompt.

#. Run ``conda-build``, using the correct path name of the recipe
   directory, including your correct user name. In this example,
   the user name is "builder"::

     conda-build C:\Users\builder\pyslalib

#. Check the output to make sure the build completed
   successfully. The output also contains the location of the
   final package file and a command to upload the package to
   Cloud.

#. In case of any linker or compiler errors, modify the recipe
   and run it again.
