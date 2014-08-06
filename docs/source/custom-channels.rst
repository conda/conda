=================
 Custom Channels
=================

The easiest way to use and manage custom channels is to use `Binstar
<https://binstar.org/>`_.  Binstar hosts and serves conda packages
automatically, and there is support built into conda for Binstar, like the
ability to use a Binstar username as a channel url, without having to type
``https://conda.binstar.org/``.

However, sometimes Binstar is too heavyweight, or you may not want to upload
your packages to the internet.

Conda allows building custom repositories, which can then be served either
through a webserver, or locally using a ``file://`` url.

To create a custom channel, first organize all the packages in platform
subdirectories, like

.. code::

   channel/
     linux-64/
       package-1.0-0.tar.bz2
     osx-64/
       package-1.0.0-0.tar.bz2

The common platform names are ``win-64``, ``win-32``, ``linux-64``,
``linux-32``, and ``osx-64``.

Next, run ``conda index`` on each of the platform subdirectories, like

.. code-block:: bash

   $ conda index channel/linux-64 channel/osx-64

.. Change this to sidebar when we get a theme that supports it.

.. note::

   The ``conda index`` command is part of the ``conda-build`` package, so you may
   need to ``conda install conda-build`` to get it.

The ``conda index`` command generates the ``repodata.json`` file, which conda
uses to get the metadata for the packages in the channel. Whenever you add or
modify a package in the channel, you will need to re-run ``conda index``.

This is it. You can now serve ``channel`` up using a webserver, or using a
``file://`` url to the ``channel`` directory.  The channel url should not
include the platform part, as conda will add it automatically. For example,
the ``file://`` url for the above example, if ``channel`` were at
``/opt/channel`` would be ``file:///opt/channel``.
