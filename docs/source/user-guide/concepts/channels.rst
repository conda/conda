========
Channels
========

.. _concepts-channels:

What is a "channel"?
====================

Channels are the locations where packages are stored.
They serve as the base for hosting and managing packages.
Conda :doc:`packages <../concepts/packages>` are downloaded
from remote channels, which are URLs to directories
containing conda packages.
The ``conda`` command searches a set of channels. By default,
packages are automatically downloaded and updated from
the `default channel`_, which may require a
paid license, as described in the `repository terms of service`_.
The ``conda-forge`` channel is free for all to use.
You can modify which remote channels are automatically searched;
this feature is beneficial when maintaining a private or internal channel.
For details, see how to :ref:`modify your channel lists <config-channels>`.

We use conda-forge as an example channel.
`Conda-forge <https://conda-forge.org/>`_ is a community channel
made up of thousands of contributors. Conda-forge itself is
analogous to PyPI but with a unified,
automated build infrastructure and more peer review of
recipes.

.. _`repository terms of service`: https://www.anaconda.com/terms-of-service

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

* In .condarc, use the key ``channels`` to see a list of channels for conda to search for packages.

Learn more about :doc:`managing channels <../tasks/manage-channels>`.

.. _rss-feed:

Conda clone channel RSS feed
============================

We offer a RSS feed that represents all the things
that have been cloned by the channel clone and are
now available behind the CDN (content delivery network).
The RSS feed shows what has happened on a rolling,
two-week time frame and is useful for seeing where
packages are or if a sync has been run.

Let's look at the `conda-forge channel RSS feed <https://conda-static.anaconda.org/conda-forge/rss.xml>`_
as an example.

In that feed, it will tell you every time that it runs a sync.
The feed includes other entries for packages that were added or
removed. Each entry is formatted to show the subdirectory
the package is from, the action that was taken (addition or removal),
and the name of the package. Everything has a publishing date,
per standard RSS practice.

.. code-block:: xml

  <rss version="0.91">
    <channel>
      <title>conda-forge updates</title>
      <link>https://anaconda.org</link>
      <description>Updates in the last two weeks</description>
      <language>en</language>
      <copyright>Copyright 2019, Anaconda, Inc.</copyright>
      <pubDate>30 Jul 2019 19:45:47 UTC</pubDate>
        <item>
          <title>running sync</title>
          <pubDate>26 Jul 2019 19:26:36 UTC</pubDate>
        </item>
        <item>
          <title>linux-64:add:jupyterlab-1.0.4-py36_0.tar.bz2</title>
          <pubDate>26 Jul 2019 19:26:36 UTC</pubDate>
        </item>
        <item>
          <title>linux-64:add:jupyterlab-1.0.4-py37_0.tar.bz2</title>
          <pubDate>26 Jul 2019 19:26:36 UTC</pubDate>
        </item>

.. _`default channel`: https://repo.anaconda.com/pkgs/
