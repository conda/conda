==============
Conda channels
==============

.. contents::
   :local:
   :depth: 1

.. _concepts-channels:

What is a "conda channel"?
==========================

Conda :doc:`packages <../concepts/packages>` are downloaded
from remote channels, which are URLs to directories
containing conda packages.
The ``conda`` command searches a default set of channels,
and packages are automatically downloaded and updated from
https://repo.anaconda.com/pkgs/.
You can modify what remote channels are automatically searched.
You might want to do this to maintain a private or internal channel.
For details, see how to :ref:`modify your channel lists <config-channels>`.

We use conda-forge as an example channel.
`Conda-forge <https://conda-forge.org/>`_ is a community channel
made up of thousands of contributors. Conda-forge itself is analogous to PyPI
but with a unified, automated build infrastructure and more peer review of
recipes.

.. _specifying-channels:

Specifying channels when installing packages
============================================

* From the command line use `--channel`

.. code-block:: bash

  $ conda install scipy --channel conda-forge
  
You may specify multiple channels by passing the argument multiple times:

.. code-block:: bash

  $ conda install scipy --channel conda-forge --channel bioconda
  
Priority decreases from left to right - the first argument is higher priority than the second.

* From the command line use `--override-channels` to only search the specified channel(s), rather than any channels configured in .condarc. This also ignores conda's default channels.

.. code-block:: bash

  $ conda search scipy --channel file:/<path to>/local-channel --override-channels

* In .condarc, use the key `channels` to see a list of channels for conda to search for packages.

Learn more about :doc:`managing channels <../tasks/manage-channels>`.

