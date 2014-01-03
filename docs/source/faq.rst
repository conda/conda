=========
Conda FAQ
=========

Table of contents:
==================

#. :ref:`sec-general-questions`
#. :ref:`sec-getting-help`
#. :ref:`sec-searching_and_info`
#. :ref:`sec-customization`
#. :ref:`sec-pkg-installation`
#. :ref:`sec-pkg-updating`
#. :ref:`sec-pkg-removing`
#. :ref:`sec-venv`

    - :ref:`sec-venv-info`
    - :ref:`sec-venv-creating`
    - :ref:`sec-venv-onoff`
    - :ref:`sec-venv-installation`
    - :ref:`sec-venv-removing`

#. :ref:`sec-recipes`

.. _sec-general-questions:

General questions
=================

#. What is anaconda?

*Anaconda* is a meta package for *conda*. This meta package contains all standard
packages (like *scipy*, *numpy*, *zlib* etc.) provided by developers from ``Continuum Analytics``.

.. _sec-getting-help:

Getting help
============

#. How can I get help for supported commands?

.. code-block:: bash

    $ conda -h

#. How can I get help for X command (e.g. **create**)?

.. code-block:: bash

    $ conda create -h

.. _sec-searching_and_info:

Searching & info
================

#. How can I find out what version of *conda* I have installed?

- by typing:
.. code-block:: bash

    $ conda info

- or by typing:

.. code-block:: bash

    $ conda -V

#. How can I check if package X (e.g. *scipy*) is available for installation?

.. code-block:: bash

    $ conda search scipy

#. How can I check if package X (e.g. *scipy*) is available for installation
   from the Continuum repos (i.e., from Anaconda)?

.. code-block:: bash

    $ conda search --override-channels --channel defaults scipy

#. How do I check if package X (e.g. *iminuit*) exists in channel Y (e.g. http://conda.binstar.org/mutirri) and is available for installation?

.. code-block:: bash

    $ conda search --override-channels --channel http://conda.binstar.org/mutirri iminuit

.. _sec-customization:

Customization (.condarc file)
=============================

Sometimes to perform below commands there is a necessity to add **-f** option (aka **--force**).

#. How can I get all keys and theirs values from my .condarc file?

.. code-block:: bash

    $ conda config --get

#. How can I get value of key X (e.g. channels) from my .condarc file?

.. code-block:: bash

    $ conda config --get channels

#. How can I add a new value Y (e.g. http://conda.binstar.org/mutirri) to key X (e.g. channels)?

.. code-block:: bash

    $ conda config --add channels http://conda.binstar.org/mutirri

#. How can I remove existing value Y (e.g. http://conda.binstar.org/mutirri) from key X?

.. code-block:: bash

    $ conda config --remove channels http://conda.binstar.org/mutirri


#. How can I remove key X (e.g. channels) and all of its values?

.. code-block:: bash

    $ conda config --remove-key channels

.. _sec-pkg-installation:

Package installation (in root environment)
==========================================

#. How can I install package X (e.g. *scipy*)?

.. code-block:: bash

    $ conda install scipy

#. How can I install package X (e.g. *scipy*) in specific Z.Z.Z version (0.12.0)?

.. code-block:: bash

    $ conda install scipy=0.12.0

#. How can I install many packages at once, like X1 (e.g. *scipy*) and X2 (e.g. *curl*)?

.. code-block:: bash

    $ conda install scipy curl

#. How can I install many packages at once, like X1 (e.g. *scipy*) in version Z.Z.Z (e.g. 0.12.0) and X2 (e.g. *curl*) in version A.A.A (e.g. 7.26.0)?

.. code-block:: bash

    $ conda install scipy=0.12.0 curl=7.26.0

.. _sec-pkg-updating:

Updating packages (in root environment)
=======================================

#. How can I update *conda* itself?

.. code-block:: bash

    $ conda update conda

#. What is the appropriate way of updating whole *anaconda* meta package?

.. code-block:: bash

    $ conda update conda
    $ conda update anaconda

#. How can I update package X (e.g. *scipy*)?

.. code-block:: bash

    $ conda update scipy

.. _sec-pkg-removing:

Removing packages (from root environment)
=========================================

#. How can I remove package X (e.g. *scipy*)?

.. code-block:: bash

    $ conda remove scipy

#. How can I remove multiple packages at once, like X1 (e.g. *scipy*) and X2 (e.g. *curl*)?

.. code-block:: bash

    $ conda remove scipy curl

.. _sec-venv:

Virtual environments
====================

.. _sec-venv-info:

Getting info about virtual environments
---------------------------------------

#. How can I get a list of all of my virtual environments?

.. code-block:: bash

    $ conda info -e

#. How can I list all of installed packages (not these which were installed through pip) in existing virtual environment X (e.g. ``myvenv``)?

- if You haven't ``myvenv`` active:

.. code-block:: bash

    $ conda list -n myvenv

- if You have ``myvenv`` active:

.. code-block:: bash

    $ conda list

#. How can I check if package Y (e.g. *scipy*) is already installed in existing virtual environment X (e.g. ``myvenv``)?

- the first method:

.. code-block:: bash

    $ conda list -n myvenv scipy

- the second method:

.. code-block:: bash

    $ source activate myvenv
    $ conda list scipy

.. _sec-venv-creating:

Creating new virtual environments
---------------------------------

#. How can I create a new and clean virtual environment X (e.g. ``myvenv``)?

.. code-block:: bash

    $ conda create -n myvenv python

#. How can I create a new virtual environment X (e.g. ``myvenv``) with *python* Y.Y.Y (e.g. 3.3.2) as default interpreter inside it?

.. code-block:: bash

    $ conda create -n myvenv python=3.3.2

#. How can I create a new virtual environment X (e.g. ``myvenv``) with package Y inside it (e.g. *scipy*)?

- in a single command:

.. code-block:: bash

    $ conda create -n myvenv scipy

- with more typing:

.. code-block:: bash

    $ conda create -n myvenv python
    $ conda install -n myvenv scipy

- the longest version (activating newly created virtual environment also):

.. code-block:: bash

    $ conda create -n myvenv python
    $ source activate myvenv
    $ conda install scipy

#. How can I create a new virtual environment X (e.g. ``myvenv``) with package Y (e.g. *scipy*) in version Z.Z.Z (e.g. 0.12.0) inside it?

- in a single command:

.. code-block:: bash

    $ conda create -n myvenv scipy=0.12.0

- with more typing:

.. code-block:: bash

    $ conda create -n myvenv python
    $ conda install -n myvenv scipy=0.12.0

- the longest version (activating newly created virtual environment also):

.. code-block:: bash

    $ conda create -n myvenv python
    $ source activate myvenv
    $ conda install scipy=0.12.0

.. _sec-venv-onoff:

Activating and deactivating
---------------------------

#. How can I activate the existing virtual environment X (e.g. ``myvenv``)?

.. code-block:: bash

    $ source activate myvenv

#. How can I deactivate active virtual environment X (e.g. ``myvenv``)?

.. code-block:: bash

    $ source deactivate

.. _sec-venv-installation:

Installation
------------

#. How can I install package Y (e.g. *scipy*) in existing virtual environment X (e.g. ``myvenv``)?

- first possibility:

.. code-block:: bash

    $ conda install -n myvenv scipy

- the alternate way:

.. code-block:: bash

    $ source activate myvenv
    $ conda install scipy

#. How can I install Z.Z.Z (e.g. 0.12.0) version of package Y (e.g. *scipy*) in existing virtual environment (e.g. ``myvenv``)?

- if You haven't ``myvenv`` active:

.. code-block:: bash

    $ conda install -n myvenv scipy=0.12.0

- if You have ``myvenv`` active:

.. code-block:: bash

    $ conda install scipy=0.12.0

#. How can I use pip in my virtual environment X (e.g. ``myvenv``)?

.. code-block:: bash

    $ conda install -n myvenv pip
    $ source activate myvenv
    $ pip <pip_subcommand>

#. How can I automatically install pip during creation of any of new virtual environment?

.. code-block:: bash

    $ conda config --add create_default_packages pip

After performing above command You can create a new virtual environments in standard way (the pip will be installed in all of them).

#. How can I automatically install Y package (e.g. *scipy*) during creation of any of new virtual environment?

.. code-block:: bash

    $ conda config --add create_default_packages scipy

After performing above command You can create a new virtual environments in standard way (the *scipy* will be installed in all of them).

#. How can I automatically install version of Z.Z.Z (e.g. 0.12.0) Y package (e.g. *scipy*) during creation of any of new virtual environment?

.. code-block:: bash

    $ conda config --add create_default_packages scipy=0.12.0

After performing above command You can create a new virtual environments in standard way (the *scipy* in 0.12.0 version will be installed in all of them).

#. How can I ignore packages from automatic installation during creation of new and clean virtual environment X (e.g. ``myvenv``)?

.. code-block:: bash

    $ conda create --no-default-packages -n myvenv python

.. _sec-venv-removing:

Removing
--------

#. How can I remove package Y (e.g. *scipy*) in existing virtual environment X (e.g. ``myvenv``)?

- if You haven't ``myvenv`` active:

.. code-block:: bash

    $ conda remove -n myvenv scipy

- if You have ``myvenv`` active:

.. code-block:: bash

    $ conda remove scipy

#. How can I remove existing virtual environment X (e.g. ``myvenv``)?

- first You have to get know where ``myvenv`` is placed (by default it will be in ${HOME}/anaconda/envs directory):

.. code-block:: bash

    $ conda info -e|grep myvenv

- then type:

.. code-block:: bash

    $ rm -rf <path_to_myvenv_directory_get_earlier>

.. _sec-recipes:

Recipes
=======

#. How can I automatically create conda recipe for currently not existing X
   package (e.g. *bottle*) if I know that this package resides on PiPY?

.. code-block:: bash

    $ conda skeleton pypi bottle

#. How can I automatically create recipe, build and install not existing currently X package
   (e.g. *bottle*) if I know that this package resides on PiPY?

.. code-block:: bash

    $ conda build --build-recipe bottle

- to install just created package in root environment, You need to find out first where the recipe was written:

.. code-block:: bash

    $ conda info

- get path from ``root environment`` variable and perform the installation:

.. code-block:: bash

    $ conda install <path_from_root_environment_variable>/conda-bld/<your_platform>/bottle.tar.bz2

- and newly created recipe You can find in <path_from_root_environment_variable>/conda-recipes/bottle
