=================
Managing packages
=================

.. contents::
   :local:
   :depth: 1

NOTE: There are many options available for the commands described
on this page. For details, see :doc:`../../commands`.


Searching for packages
=======================

Use the Terminal or an Anaconda Prompt for the following steps.

To see if a specific package such as SciPy is available for
installation:

.. code-block:: bash

   conda search scipy

To see if a specific package such as SciPy is available for
installation from Anaconda.org:

.. code-block:: bash

   conda search --override-channels --channel defaults scipy

To see if a specific package, such as iminuit, exists in a
specific channel, such as http://conda.anaconda.org/mutirri,
and is available for installation:

.. code-block:: bash

   conda search --override-channels --channel http://conda.anaconda.org/mutirri iminuit


Installing packages
===================

Use the Terminal or an Anaconda Prompt for the following steps.

To install a specific package such as SciPy into an existing
environment "myenv":

.. code-block:: bash

   conda install --name myenv scipy

If you do not specify the environment name, which in this
example is done by ``--name myenv``, the package installs
into the current environment:

.. code-block:: bash

   conda install scipy

To install a specific version of a package such as SciPy:

.. code-block:: bash

   conda install scipy=0.15.0

.. _`installing multiple packages`:

To install multiple packages at once, such as SciPy and cURL:

.. code-block:: bash

   conda install scipy curl

NOTE: It is best to install all packages at once, so that all of
the dependencies are installed at the same time.

To install multiple packages at once and specify the version of
the package:

.. code-block:: bash

   conda install scipy=0.15.0 curl=7.26.0

To install a package for a specific Python version:

.. code-block:: bash

   conda install scipy=0.15.0 curl=7.26.0 -n py34_env

If you want to use a specific Python version, it is best to use
an environment with that version. For more information,
see :doc:`../troubleshooting`.


Installing packages from Anaconda.org
=======================================

Packages that are not available using conda install can be
obtained from Anaconda.org. Formerly Binstar.org, Anaconda.org,
is a package management service for both public and private
package repositories. Anaconda.org is an Anaconda
product, just like Anaconda and Miniconda.

To install a package from Anaconda.org:

#. In a browser, go to http://anaconda.org.

#. To find the package named bottleneck, type ``bottleneck``
   in the top-left box named Search Packages.

#. Find the package that you want and click it to go to the
   detail page.

   The detail page displays the name of the channel. In this
   example it is the "pandas" channel.

#. Now that you know the channel name, use the ``conda install``
   command to install the package. In your Terminal window or an Anaconda Prompt,
   run:

   .. code::

      conda install -c pandas bottleneck

   This command tells conda to install the bottleneck package
   from the pandas channel on Anaconda.org.

#. To check that the package is installed, in your Terminal window or an Anaconda Prompt,
   run:

   .. code::

      conda list

   A list of packages appears, including bottleneck.

NOTE: For information on installing packages from multiple
channels, see :doc:`manage-channels`.


Installing non-conda packages
=============================

If a package is not available from conda or Anaconda.org,
you may be able to find and install the package with another
package manager like pip.

NOTE: Both pip and conda are included in Anaconda and Miniconda,
so you do not need to install them separately.

NOTE: Conda environments replace virtualenv, so there is no need
to activate a virtualenv before using pip.

To install a non-conda package:

#. Activate the environment where you want to put the program:

   * On Windows, in your Anaconda Prompt, run ``activate myenv``.
   * On macOS and Linux,in your Terminal window, run ``source activate myenv``.

#. To use pip to install a program such as See, in your Terminal window or an Anaconda Prompt,
   run::

     pip install see

#. To verify the package was installed, in your Terminal window or an Anaconda Prompt,
   run:

   .. code::

      conda list


Installing commercial packages
==============================

Installing a commercial package such as IOPro is the same as
installing any other package. In your Terminal window or an Anaconda Prompt,
run:

.. code-block:: bash

   conda install --name myenv iopro

This command installs a free trial of one of Anaconda's
commercial packages called `IOPro
<https://docs.continuum.io/iopro/>`_, which can speed up your
Python processing. Except for academic use, this free trial
expires after 30 days.


Viewing a list of installed packages
====================================

Use the Terminal or an Anaconda Prompt for the following steps.

To list all of the packages in the active environment:

.. code::

   conda list

To list all of the packages in a deactivated environment:

.. code::

   conda list -n myenv


Updating packages
=================

Use ``conda update`` command to check to see if a new update is
available. If conda tells you an update is available, you can
then choose whether or not to install it.

Use the Terminal or an Anaconda Prompt for the following steps.

To update a specific package:

.. code::

   conda update biopython

To update Python:

.. code::

   conda update python

To update conda itself:

.. code::

   conda update conda

NOTE: Conda updates to the highest version in its series, so
Python 2.7 updates to the highest available in the 2.x series and
3.6 updates to the highest available in the 3.x series.

To update the Anaconda metapackage:

.. code-block:: bash

   conda update conda
   conda update anaconda

Regardless of what package you are updating, conda compares
versions and then reports what is available to install. If no
updates are available, conda reports "All requested packages are
already installed."

If a newer version of your package is available and you wish to
update it, type ``y`` to update:

.. code::

   Proceed ([y]/n)? y


.. _pinning-packages:

Preventing packages from updating (pinning)
===========================================

Pinning a package specification in an environment prevents
packages listed in the ``pinned`` file from being updated.

In the environment's ``conda-meta`` directory, add a file
named ``pinned`` that includes a list of the packages that you
do not want updated.

EXAMPLE: The file below forces NumPy to stay on the 1.7 series,
which is any version that starts with 1.7, and forces SciPy to
stay at exactly version 0.14.2::

  numpy 1.7.*
  scipy ==0.14.2

With this ``pinned`` file, ``conda update numpy`` keeps NumPy at
1.7.1, and ``conda install scipy=0.15.0`` causes an error.

Use the ``--no-pin`` flag to override the update restriction on
a package. In the Terminal or an Anaconda Prompt, run:

.. code-block:: bash

   conda update numpy --no-pin

Because the ``pinned`` specs are included with each conda
install, subsequent ``conda update`` commands without
``--no-pin`` will revert NumPy back to the 1.7 series.


Removing packages
=================

Use the Terminal or an Anaconda Prompt for the following steps.

To remove a package such as SciPy in an environment such as
myenv:

.. code-block:: bash

   conda remove -n myenv scipy

To remove a package such as SciPy in the current environment:

.. code-block:: bash

   conda remove scipy

To remove multiple packages at once, such as SciPy and cURL:

.. code-block:: bash

   conda remove scipy curl

To confirm that a package has been removed:

.. code::

   conda list
