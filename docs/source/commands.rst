=================
Command Reference
=================

Conda provides many commands for managing packages and environments.  The
following pages have help for each command. The help for a command can also be
accessed from the command line with the ``--help`` flag:

.. code-block:: bash

   conda install --help


:doc:`general-commands`
=======================

.. toctree::
   :glob:
   :maxdepth: 2

   commands/*


:doc:`env-commands`
===================

The following commands are part of the ``conda-env`` package, which is
installed automatically with conda.

.. toctree::
   :glob:
   :maxdepth: 2

   commands/env/*


:doc:`build-commands`
=====================

The following commands are part of the ``conda-build`` package, which can be
installed with ``conda install conda-build``.

.. toctree::
   :glob:
   :maxdepth: 2

   commands/build/*

