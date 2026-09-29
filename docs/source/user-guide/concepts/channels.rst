========
Channels
========

.. _concepts-channels:

What is a "channel"?
====================

Channels are locations where conda packages are stored. A channel can be
a public package repository, a private or internal package repository, or
a local directory on your computer.

Conda :doc:`packages <../concepts/packages>` are downloaded from channels,
which are URLs or channel names that point to directories containing conda
packages. The ``conda`` command searches a configured set of channels when
you install, update, or search for packages.

By default, packages are automatically downloaded and updated from the
`default channel`_, which may require a paid license, as described in the
`repository terms of service`_. You can modify which channels conda
searches. For details, see how to :ref:`modify your channel lists
<config-channels>`.

Common public channels
======================

Some commonly used public channels and multichannels include:

``defaults``
    A built-in multichannel that includes Anaconda-hosted channels such as
    ``main``, ``r``, and ``msys2`` under ``repo.anaconda.com``.

``main``
    The primary Anaconda-hosted channel under ``repo.anaconda.com``. It
    contains many commonly used packages distributed by Anaconda.

``conda-forge``
    A community-led channel with packages maintained by thousands of
    contributors. The `conda-forge project <https://conda-forge.org/>`_
    provides a large collection of packages across many ecosystems.

``bioconda``
    A community channel focused on bioinformatics packages. The
    `Bioconda project <https://bioconda.github.io/>`_ is commonly used
    together with ``conda-forge``.

You can browse public channels and search for packages on
`Anaconda.org <https://anaconda.org/>`_.

.. _`repository terms of service`: https://www.anaconda.com/terms-of-service

.. _specifying-channels:

Specifying channels when installing packages
============================================

From the command line, use ``--channel`` to search a specific channel:

.. code-block:: bash

  $ conda install scipy --channel conda-forge

You may specify multiple channels by passing the argument multiple times:

.. code-block:: bash

  $ conda install scipy --channel conda-forge --channel bioconda

Priority decreases from left to right: the first argument has higher
priority than the second.

Use ``--override-channels`` to search only the specified channel or
channels instead of any channels configured in ``.condarc``. This also
ignores conda's default channels.

.. code-block:: bash

  $ conda search scipy --channel conda-forge --override-channels

In ``.condarc``, use the ``channels`` key to configure the list of
channels conda searches for packages.

Learn more about :doc:`managing channels <../tasks/manage-channels>`.

Local channels
==============

A local channel is a channel stored on your own computer or on a shared
filesystem. Local channels are useful when you are building your own
packages, testing packages before publishing them, or maintaining packages
for an internal workflow.

Local channels use the same channel layout as remote channels. They contain
platform subdirectories such as ``linux-64``, ``osx-64``, ``win-64``, and
``noarch``. Each subdirectory contains package files and repository metadata.

To use a local channel, provide a ``file://`` URL or path to the channel
root. For example:

.. code-block:: bash

  $ conda search --channel file:///opt/conda-channel --override-channels

For a step-by-step example of creating and indexing a local channel, see
:doc:`creating custom channels <../tasks/create-custom-channels>`.

.. _`default channel`: https://repo.anaconda.com/pkgs/
