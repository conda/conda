==================
Conda environments
==================

A conda environment is a directory that contains a specific
collection of conda packages that you have installed. For
example, you may have one environment with NumPy 1.7 and its
dependencies, and another environment with NumPy 1.6 for legacy
testing. If you change one environment, your other environments
are not affected. You can easily activate or deactivate
environments, which is how you switch between them. You can also
share your environment with someone by giving them a copy of your
``environment.yaml`` file. For more information, see
:doc:`../tasks/manage-environments`.


Conda directory structure
=========================

``ROOT_DIR``
------------
The directory that Anaconda or Miniconda was installed into.

EXAMPLES:

.. code-block:: shell

   /opt/Anaconda  #Linux
   C:\Anaconda    #Windows

``/pkgs``
---------

Also referred to as PKGS_DIR. This directory contains
decompressed packages, ready to be linked in conda environments.
Each package resides in a subdirectory corresponding to its
canonical name.

``/envs``
---------

The system location for additional conda environments to be
created.

The following subdirectories comprise the default Anaconda
environment:

| ``/bin``
| ``/include``
| ``/lib``
| ``/share``
|

Other conda environments usually contain the same subdirectories
as the default environment.