======================
Using the free channel
======================

The free channel contains packages created prior to
September 26, 2017. Prior to conda 4.7, the free
channel was part of the ``defaults`` channel.
Read more about the :ref:`defaults channel <default-channels>`.

Removing the ``free`` channel reduced conda's search space
and hid old software. That old software could have incompatible
constraint information. Read more about `why we made this change
<https://www.anaconda.com/why-we-removed-the-free-channel-in-conda-4-7/>`_.


If you still need the content from the ``free`` channel to reproduce
old environments, you can re-add the channel following the directions below.

.. _free-channel-default:

Adding the free channel to defaults
===================================

If you want to add the ``free`` channel back into your default list,
use the command::

   conda config --set restore_free_channel true

The order of the channels is important. Using the above
command will restore the ``free`` channel in the correct order.

Changing .condarc
=================

You can also add the ``free`` channel back into your defaults by
changing the ``.condarc`` file itself.

Add the following to the conda section of your ``.condarc`` file::

   restore_free_channel: true

Read more about :doc:`use-condarc`.

Package name changes
====================

Some packages that are available in the ``free`` channel
have different names in the ``main`` channel.

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Package name in ``free``
     - Package name in ``main``
   * - dateutil
     - python-dateutil
   * - gcc
     - gcc_linux-64 and similar
   * - pil
     - pillow
   * - ipython-notebook
     - now installable via notebook, a metapackage could be created
   * - Ipython-qtconsole
     - now installable via qtconsole, a metapackage could be created
   * - beautiful-soup
     - beautifulsoup4
   * - pydot-ng
     - pydot


Troubleshooting
===============

You may encounter some errors, such as UnsatisfiableError
or a PackagesNotFoundError.

An example of this error is::

   $ conda create -n test -c file:///Users/jsmith/anaconda/conda-bld bad_pkg
   Collecting package metadata: done
   Solving environment: failed

   UnsatisfiableError: The following specifications were found to be in conflict:
     - cryptography=2.6.1 -> openssl[version='>=1.1.1b,<1.1.2a']
     - python=3.7.0 -> openssl[version='>=1.0.2o,<1.0.3a']
   Use "conda search <package> --info" to see the dependencies for each package.

This can occur if:

- you’re trying to install a package that is only available in
  ``free`` and not in ``main``.
- you have older environments in files you want to recreate.
  If those spec files reference packages that are in ``free``,
  they will not show up.
- a package is dependent upon files found only in the free
  channel. Conda will not let you install the package if it cannot
  install the dependency, which the package requires to work.

If you encounter these errors, consider using a newer package than
the one in ``free``. If you want those older versions, you can
:ref:`add the free channel back into your defaults
<free-channel-default>`.
