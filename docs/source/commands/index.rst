=================
Command reference
=================

.. contents::
   :local:
   :depth: 1

Conda provides many commands for managing packages and environments.
The links on this page provide help for each command.
You can also access help from the command line with the
``--help`` flag:

.. code-block:: bash

   conda install --help

The following commands are part of conda:

.. toctree::
   :glob:
   :maxdepth: 2

   clean
   compare
   config
   create
   doctor
   env/index
   info
   init
   install
   list
   notices
   package
   remove
   rename
   run
   search
   update

Conda vs. pip vs. virtualenv commands
=====================================

If you have used pip and virtualenv in the past, you can use
conda to perform all of the same operations. Pip is a package
manager and virtualenv is an environment manager. conda is both.

Scroll to the right to see the entire table.

.. list-table::
   :widths: 5 15 15 15
   :header-rows: 1

   * - Task
     - Conda package and environment manager command
     - Pip package manager command
     - Virtualenv environment manager command
   * - Install a package
     - ``conda install $PACKAGE_NAME``
     - ``pip install $PACKAGE_NAME``
     - X
   * - Update a package
     - ``conda update --name $ENVIRONMENT_NAME $PACKAGE_NAME``
     - ``pip install --upgrade $PACKAGE_NAME``
     - X
   * - Update package manager
     - ``conda update conda``
     - Linux/macOS: ``pip install -U pip`` Win: ``python -m pip install -U pip``
     - X
   * - Uninstall a package
     - ``conda remove --name $ENVIRONMENT_NAME $PACKAGE_NAME``
     - ``pip uninstall $PACKAGE_NAME``
     - X
   * - Create an environment
     - ``conda create --name $ENVIRONMENT_NAME python``
     - X
     - ``cd $ENV_BASE_DIR; virtualenv $ENVIRONMENT_NAME``
   * - Activate an environment
     - ``conda activate $ENVIRONMENT_NAME``\*
     - X
     - ``source $ENV_BASE_DIR/$ENVIRONMENT_NAME/bin/activate``
   * - Deactivate an environment
     - ``conda deactivate``
     - X
     - ``deactivate``
   * - Search available packages
     - ``conda search $SEARCH_TERM``
     - ``pip search $SEARCH_TERM``
     - X
   * - Install package from specific source
     - ``conda install --channel $URL $PACKAGE_NAME``
     - ``pip install --index-url $URL $PACKAGE_NAME``
     - X
   * - List installed packages
     - ``conda list --name $ENVIRONMENT_NAME``
     - ``pip list``
     - X
   * - Create requirements file
     - ``conda list --export``
     - ``pip freeze``
     - X
   * - List all environments
     - ``conda info --envs``
     - X
     - Install virtualenv wrapper, then ``lsvirtualenv``
   * - Install other package manager
     - ``conda install pip``
     - ``pip install conda``
     - X
   * - Install Python
     - ``conda install python=x.x``
     - X
     - X
   * - Update Python
     - ``conda update python``\*
     - X
     - X


\* ``conda activate`` only works on conda 4.6 and later versions.
For conda versions prior to 4.6, type:

   * Windows: ``activate``
   * Linux and macOS: ``source activate``

\* ``conda update python`` updates to the most recent in the series,
so any Python 2.x would update to the latest 2.x and any Python 3.x
to the latest 3.x.


.. Show what files a package has installed ``pip show --files $PACKAGE_NAME``  not possible
.. Print details on an individual package ``pip show $PACKAGE_NAME``  not possible
.. List available environments   not possible   ``conda info -e``
.. #user will want to pass that through ``tail -n +3 | awk '{print $1;}'``
