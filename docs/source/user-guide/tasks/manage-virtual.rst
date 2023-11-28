=========================
Managing virtual packages
=========================

"Virtual" packages are injected into the conda solver to allow real packages
to depend on features present on the system that cannot be managed directly by
conda, like system driver versions or CPU features. Virtual packages are not
real packages and not displayed by ``conda list``. Instead ``conda`` runs a
small bit of code to detect the presence or absence of the system feature that
corresponds to the package. The currently supported list of virtual packages includes:

  * ``__cuda``: Maximum version of CUDA supported by the display driver.
  * ``__osx``: OSX version if applicable.
  * ``__glibc``: Version of glibc supported by the OS.
  * ``__linux``: Available when running on Linux.
  * ``__unix``: Available when running on OSX or Linux.
  * ``__win``: Available when running on Win.

Other virtual packages will be added in future conda releases. These are denoted
by a leading double-underscore in the package name.

.. note::

   Note that as of version ``22.11.0``,
   :doc:`virtual packages <../../dev-guide/plugins/virtual_packages>` are
   implemented as :doc:`conda plugins <../../user-guide/concepts/conda-plugins>`.

Listing detected virtual packages
=================================

Use the terminal or an Anaconda Prompt for the following steps.

To see the list of detected virtual packages, run:

.. code-block:: bash

   conda info

If a package is detected, you will see it listed in the ``virtual packages``
section, as shown in this example::

         active environment : base
        active env location : /Users/demo/dev/conda/devenv
                shell level : 1
           user config file : /Users/demo/.condarc
     populated config files : /Users/demo/.condarc
              conda version : 4.6.3.post8+8f640d35a
        conda-build version : 3.17.8
             python version : 3.7.2.final.0
           virtual packages : __cuda=10.0
           base environment : /Users/demo/dev/conda/devenv (writable)
               channel URLs : https://repo.anaconda.com/pkgs/main/osx-64
                              https://repo.anaconda.com/pkgs/main/noarch
                              https://repo.anaconda.com/pkgs/free/osx-64
                              https://repo.anaconda.com/pkgs/free/noarch
                              https://repo.anaconda.com/pkgs/r/osx-64
                              https://repo.anaconda.com/pkgs/r/noarch
              package cache : /Users/demo/dev/conda/devenv/pkgs
                              /Users/demo/.conda/pkgs
           envs directories : /Users/demo/dev/conda/devenv/envs
                              /Users/demo/.conda/envs
                   platform : osx-64
                 user-agent : conda/4.6.3.post8+8f640d35a requests/2.21.0 CPython/3.7.2 Darwin/17.7.0 OSX/10.13.6
                    UID:GID : 502:20
                 netrc file : None
               offline mode : False


Overriding detected packages
============================

For troubleshooting, it is possible to override virtual package detection
using an environment variable. Supported variables include:

* ``CONDA_OVERRIDE_CUDA`` - CUDA version number or set to ``""`` for no CUDA
  detected.
* ``CONDA_OVERRIDE_OSX`` - OSX version number or set to ``""`` for no OSX
  detected.
* ``CONDA_OVERRIDE_GLIBC`` - GLIBC version number or set to ``""`` for no GLIBC.
  This only applies on Linux.
