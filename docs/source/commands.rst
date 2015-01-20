=================
Command Reference
=================

Conda provides many commands for managing packages and environments.  The
following pages have help for each command. The help for a command can also be
accessed from the command line with the ``--help`` flag, like

.. code-block:: bash

   conda install --help

Contents:

.. toctree::
   :glob:
   :maxdepth: 2

   commands/*

conda-build commands
====================

The following commands are part of the ``conda-build`` package, which can be
installed with ``conda install conda-build``.

.. toctree::
   :glob:
   :maxdepth: 2

   commands/build/*

conda-pip rosetta stone
=======================
If you've used pip and virtualenv in the past, you can use conda to perform the operations you are used to.

=====================================   =======================================================   ===========================================================
Operation                               Pip Command                                               Conda Command
=====================================   =======================================================   ===========================================================
Install a package                       ``pip install $PACKAGE_NAME``                             ``conda install $PACKAGE_NAME``
Uninstall a package                     ``pip uninstall $PACKAGE_NAME``                           ``conda remove --name $ENVIRONMENT_NAME $PACKAGE_NAME``
Create an environment                   ``cd $ENV_BASE_DIR; virtualenv $ENVIRONMENT_NAME``        ``conda create --name $ENVIRONMENT_NAME python``
Activate an environment                 ``source $ENV_BASE_DIR/$ENVIRONMENT_NAME/bin/activate``   ``source activate $ENVIRONMENT_NAME``
Deactivate an environment               ``deactivate``                                            ``source deactivate``
Search available packages               ``pip search $SEARCH_TERM``                               ``conda search $SEARCH_TERM``
Install package from specific source    ``pip install --index-url $URL $PACKAGE_NAME``            ``conda install --channel $URL $PACKAGE_NAME``
List installed packages                 ``pip list``                                              ``conda list --name $ENVIRONMENT_NAME``
Create requirements file                ``pip freeze``                                            ``conda list --export``
Update a package                        ``pip install --upgrade $PACKAGE_NAME``                   ``conda update --name $PACKAGE_NAME``
=====================================   =======================================================   ===========================================================

.. Show what files a package has installed ``pip show --files $PACKAGE_NAME``  not possible
.. Print details on an individual package ``pip show $PACKAGE_NAME``  not possible
.. List available environments   not possible   ``conda info -e``
.. #user will want to pass that through ``tail -n +3 | awk '{print $1;}'``
