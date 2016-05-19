=================
Managing packages
=================

.. contents::

Before you begin, you should have installed Miniconda or Anaconda, and gone through the previous :doc:`Managing environments <envs>` section. That means you have already installed a few packages when you created a new environment. 

NOTE: There are many options available for each of these commands. See the :doc:`Command reference </commands>` for more detail. 

List all packages
~~~~~~~~~~~~~~~~~

List all of your packages in the active environment:

.. code::

   conda list

To list all of your packages installed into a non-active environment named snowflakes:

.. code::

   conda list -n snowflakes

Search for a package
~~~~~~~~~~~~~~~~~~~~

To see if a specific package is available for conda to install: 

.. code::

   conda search beautiful-soup

This displays the package name, so we know it is available. 

Install a package
~~~~~~~~~~~~~~~~~

Install a package such as "Beautiful Soup" into the current environment, using conda install as follows: 

.. code::

   conda install --name bunnies beautiful-soup

NOTE: If you do not specify the name of the environment where you want it installed (--name bunnies) it will install in the current environment. 


Activate the bunnies environment, and do a conda list to see the new program installed:

**Linux, OS X:** ``source activate bunnies``
**Windows:**  ``activate bunnies``

**All:**  ``conda list``

NOTE: Installing a commercial package (such as IOPro) is the same as installing any other package: ``conda install --name bunnies iopro``

Install a package from Anaconda.org 
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For packages that are not available using conda install, we can look in the repository Anaconda.org. Anaconda.org, formerly Binstar.org, is a package management service for both public and private package repositories. Anaconda.org is a Continuum Analytics product, just like Anaconda and Miniconda. 

In a browser, go to http://anaconda.org.  To find the package named "bottleneck" enter that search term in the top left box named "Search Packages."

Find the package you want and click to go to the detail page. There you will see the name of the channel -- in this case it is the "pandas" channel. 

Now that you know the channel name, you can use the ``conda install`` command to get it:

.. code::

   conda install -c pandas bottleneck 

That means "Conda install the Bottleneck package from the Pandas channel on Anaconda.org."

The package will install. 

Check to see that the package is now installed: 

.. code::

   conda list

You will see a list of packages, including Bottleneck.


Install non-conda packages 
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If a package is not available from conda or Anaconda.org, you may be able to find and install the package with another package manager like pip. 

NOTE: Both pip and conda are already included in Anaconda and Miniconda, so you do not need to install them separately. 

NOTE: Conda environments replace virtualenv so there's no need to activate a virtualenv before using pip.

Activate the environment where you want to put the program, then pip install a program named "See": 

**Linux, OS X:** ``source activate bunnies``

**Windows:**  ``activate bunnies``

**All:**  ``pip install see``

Check to see that the See package was installed by pip:  

.. code::

   conda list

Install a commercial package
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Installing commercial packages is the same as installing any other package with conda. So as an example, let’s install and then delete a free trial of one of Continuum’s commercial packages IOPro, which can speed up your Python processing:

.. code::

   conda install iopro 

TIP: Except for academic use, this free trial expires after 30 days. 

You can now install and verify any package you want using conda, whether using the conda command, downloading from Anaconda.org, or using pip install, and whether open source or commercial. 

Package update
~~~~~~~~~~~~~~~~~

You can check to see if a new update is available with the conda update command. If conda tells you an update is available, you can then choose whether or not to install it.

Use the conda update command to update a specific package:  

.. code::

   conda update biopython

You can use the conda update command to update conda itself:

.. code::

   conda update conda

You can also update Python with the update command:

.. code::

   conda update python

NOTE: Conda will update to the highest version in its series, so Python 2.7 will update to the highest available in the 2.x series, and 3.5 will update to the highest available in the 3.x series.

Regardless of what package you are updating, conda will compare versions, then let you know what is available to install. If none are available, conda will reply "All requested packages are already installed."

If a newer version of your package is available, and you wish to update it, type Y to update:
 
.. code::

   Proceed ([y]/n)? y

Type "y" for yes.

Package remove
~~~~~~~~~~~~~~~~~

If you decide not to continue using a package, for example, the commercial package IOPro, you can remove it from the bunnies environment with:

.. code::

   conda remove --name bunnies iopro

Confirm that the package has been removed: 

.. code::

   conda list

Next, let's take a look at :doc:`/r-with-conda`.
