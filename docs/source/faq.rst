=========
Conda FAQ
=========

Table of contents:
==================

#. :ref:`general-questions`
#. :ref:`getting-help`
#. :ref:`searching_and_info`
#. :ref:`customization`
#. :ref:`pkg-installation`
#. :ref:`pkg-updating`
#. :ref:`pkg-removing`
#. :ref:`env`

    - :ref:`env-info`
    - :ref:`env-creating`
    - :ref:`env-onoff`
    - :ref:`env-installation`
    - :ref:`env-removing`

#. :ref:`recipes`

.. _general-questions:

General questions
=================

#. What is anaconda?

   *Anaconda* is a meta package for *conda*. This meta package contains all standard
   packages (like *scipy*, *numpy*, *zlib* etc.) provided by developers from ``Continuum Analytics``.

.. _getting-help:

Getting help
============

#. How can I see what conda commands are supported?

   .. code-block:: bash

      $ conda -h

#. How can I get help for X command (e.g. **create**)?

   .. code-block:: bash

      $ conda create -h

.. _searching_and_info:

Searching & info
================

#. How can I find out what version of *conda* I have installed?

   By typing:

   .. code-block:: bash

      $ conda info

   or by typing:

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

.. _customization:

Customization (.condarc file)
=============================

.. note::

   Sometimes to perform the below commands it is necessary to add the **-f** option
   (aka **--force**).

#. How can I get all keys and their values from my .condarc file?

   .. code-block:: bash

      $ conda config --get

#. How can I get the value of key X (e.g. channels) from my .condarc file?

   .. code-block:: bash

      $ conda config --get channels

#. How can I add a new value Y (e.g. http://conda.binstar.org/mutirri) to key X (e.g. channels)?

   .. code-block:: bash

      $ conda config --add channels http://conda.binstar.org/mutirri

#. How can I remove existing value Y (e.g. http://conda.binstar.org/mutirri) from key X?

   .. code-block:: bash

      $ conda config --remove channels http://conda.binstar.org/mutirri

#. How can I remove the key X (e.g. channels) and all of its values?

   .. code-block:: bash

      $ conda config --remove-key channels

.. _pkg-installation:

Package installation (in the root environment)
==============================================

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

.. _pkg-updating:

Updating packages (in the root environment)
===========================================

#. How can I update *conda* itself?

   .. code-block:: bash

      $ conda update conda

#. How do I update the *anaconda* meta package?

   .. code-block:: bash

      $ conda update conda
      $ conda update anaconda

#. How can I update package X (e.g. *scipy*)?

   .. code-block:: bash

      $ conda update scipy

.. _pkg-removing:

Removing packages (from the root environment)
=============================================

#. How can I remove package X (e.g. *scipy*)?

   .. code-block:: bash

      $ conda remove scipy

#. How can I remove multiple packages at once, like X1 (e.g. *scipy*) and X2 (e.g. *curl*)?

   .. code-block:: bash

      $ conda remove scipy curl

.. _env:

Environments
============

.. _env-info:

Getting info about environments
-------------------------------

#. How can I get a list of all of my environments?

   .. code-block:: bash

      $ conda info -e

#. How can I list all installed packages in environment X (e.g. ``myenv``)?

   If ``myenv`` is not activated:

     .. code-block:: bash

        $ conda list -n myenv

   Id ``myenv`` is activated:

     .. code-block:: bash

        $ conda list

#. How can I check if package Y (e.g. *scipy*) is already installed in existing environment X (e.g. ``myenv``)?

   - the first method:

     .. code-block:: bash

        $ conda list -n myenv scipy

   - the second method:

     .. code-block:: bash

        $ source activate myenv
        $ conda list scipy

.. _env-creating:

Creating new environments
-------------------------

#. How can I create a new and clean environment X (e.g. ``myenv``)?

   .. code-block:: bash

      $ conda create -n myenv python

#. How can I create a new environment X (e.g. ``myenv``) with *python* Y.Y.Y
   (e.g. 3.3) as the default interpreter inside it?

   .. code-block:: bash

      $ conda create -n myenv python=3.3

#. How can I create a new environment X (e.g. ``myenv``) with package Y inside it (e.g. *scipy*)?

   - in a single command:

     .. code-block:: bash

        $ conda create -n myenv scipy

   - with more typing:

     .. code-block:: bash

        $ conda create -n myenv python
        $ conda install -n myenv scipy

   - the longest version (also activates the newly created environment):

     .. code-block:: bash

        $ conda create -n myenv python
        $ source activate myenv
        $ conda install scipy

#. How can I create a new environment X (e.g. ``myenv``) with package Y (e.g. *scipy*) in version Z.Z.Z (e.g. 0.12.0) inside it?

   - in a single command:

     .. code-block:: bash

        $ conda create -n myenv scipy=0.12.0

   - with more typing:

     .. code-block:: bash

        $ conda create -n myenv python
        $ conda install -n myenv scipy=0.12.0

   - the longest version (activating newly created environment also):

     .. code-block:: bash

        $ conda create -n myenv python
        $ source activate myenv
        $ conda install scipy=0.12.0

.. _env-onoff:

Activating and deactivating
---------------------------

#. How can I activate the existing environment X (e.g. ``myenv``)?

   .. code-block:: bash

      $ source activate myenv

#. How can I deactivate the active environment X (e.g. ``myenv``)?

   .. code-block:: bash

      $ source deactivate

.. _env-installation:

Installation
------------

#. How can I install package Y (e.g. *scipy*) in existing environment X (e.g. ``myenv``)?

   - first possibility:

     .. code-block:: bash

        $ conda install -n myenv scipy

   - the alternate way:

     .. code-block:: bash

        $ source activate myenv
        $ conda install scipy

#. How can I install Z.Z.Z (e.g. 0.12.0) version of package Y (e.g. *scipy*) in existing environment (e.g. ``myenv``)?

   If ``myenv`` not activated:

     .. code-block:: bash

        $ conda install -n myenv scipy=0.12.0

   If ``myenv`` is activated:

     .. code-block:: bash

        $ conda install scipy=0.12.0

#. How can I use pip in my environment X (e.g. ``myenv``)?

   .. code-block:: bash

      $ conda install -n myenv pip
      $ source activate myenv
      $ pip <pip_subcommand>

#. How can I automatically install pip during creation of any of new environment?

   .. code-block:: bash

      $ conda config --add create_default_packages pip

   After performing the above command you can create a new environment in the standard way (pip will be installed in all of them).

#. How can I automatically install Y package (e.g. *scipy*) during creation of any of new environment?

   .. code-block:: bash

      $ conda config --add create_default_packages scipy

   After performing the above command you can create a new environments in the
   standard way (the *scipy* will be installed in all of them).

#. How can I automatically install version Z.Z.Z (e.g. 0.12.0) of package Y (e.g. *scipy*) during creation of any of new environment?

   .. code-block:: bash

      $ conda config --add create_default_packages scipy=0.12.0

   After performing the above command you can create a new environments in the
   standard way (the *scipy* in 0.12.0 version will be installed in all of
   them).

#. How can I ignore packages from automatic installation during creation of new and clean environment X (e.g. ``myenv``)?

   .. code-block:: bash

      $ conda create --no-default-packages -n myenv python

.. _env-removing:

Removing
--------

#. How can I remove package Y (e.g. *scipy*) in existing environment X (e.g. ``myenv``)?

   If ``myenv`` is not activated:

     .. code-block:: bash

        $ conda remove -n myenv scipy

   If ``myenv`` is activated:

     .. code-block:: bash

        $ conda remove scipy

#. How can I remove existing environment X (e.g. ``myenv``)?

     .. code-block:: bash

        $ conda remove -n myenv --all



.. _recipes:

Recipes
=======

#. How can I create a skeleton conda recipe for package X (e.g. *bottle*) if I
   know that this package is on PyPI?

   .. code-block:: bash

      $ conda skeleton pypi bottle

   You can then build it with

   .. code-block:: bash

      $ conda build bottle

   It is recommended to upload the package to binstar when you are done. Then
   if you add your binstar channel to your .condarc (see :ref:`customization`
   above), you will be able to install the package with

   .. code-block:: bash

      $ conda install bottle

   - If you did not upload the package to binstar, to install this package in
     the root environment, you need to find out where the built package is:

     .. code-block:: bash

        $ conda info

   - get the ``root environment`` path and perform the installation:

     .. code-block:: bash

        $ conda install <path_from_root_environment_variable>/conda-bld/<your_platform>/bottle.tar.bz2

   This information is also shown at the end of the build process.
