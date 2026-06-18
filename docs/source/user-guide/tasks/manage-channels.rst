=================
Managing channels
=================

Conda channels are the locations where packages are stored.
They serve as the base for hosting and managing packages.
Conda packages are downloaded from remote channels, which are URLs to
directories containing conda packages. The conda command searches a default
set of channels and packages are automatically downloaded and updated
from the `default channel`_. Read more about
:doc:`conda channels <../concepts/channels>` and the various terms of service
for their use.

Different channels can have the same package, so conda must handle these
channel collisions.

There will be no channel collisions if you use only the defaults channel.
There will also be no channel collisions if all of the channels you use only
contain packages that do not exist in any of the other channels in your list.
The way conda resolves these collisions matters only when you have multiple
channels in your channel list that host the same package.

By default, conda prefers packages from a higher priority
channel over any version from a lower priority channel.
Therefore, you can put channels at the bottom of your
channel list to provide additional packages that are not in the
default channels. However, it is not recommended to mix channels
in a single environment.

Conda collects all of the packages with the same name across all
listed channels and processes them as follows:

#. Sorts packages from highest to lowest channel priority.

#. Sorts tied packages---packages with the same channel priority---from highest to
   lowest version number. For example, if channelA contains NumPy 1.12.0
   and 1.13.1, NumPy 1.13.1 will be sorted higher.

#. Sorts still-tied packages---packages with the same channel priority and same
   version---from highest to lowest build number. For example, if channelA contains
   both NumPy 1.12.0 build 1 and build 2, build 2 is sorted first. Any packages
   in channelB would be sorted below those in channelA.

#. Installs the first package on the sorted list that satisfies
   the installation specifications.

Essentially, the order goes:
channelA::numpy-1.13_1 > channelA::numpy-1.12.1_1 > channelA::numpy-1.12.1_0 > channelB::numpy-1.13_1

.. note::
   If strict channel priority is turned on then channelB::numpy-1.13_1 isn't
   included in the list at all.


To make conda install the newest version
of a package in any listed channel:

* Add ``channel_priority: disabled`` to your ``.condarc`` file.

  OR

* Run the equivalent command:

   .. code-block:: shell

      conda config --set channel_priority disabled

Conda then sorts as follows:

#. Sorts the package list from highest to lowest version number.

#. Sorts tied packages from highest to lowest channel priority.

#. Sorts tied packages from highest to lowest build number.

Because build numbers from different channels are not
comparable, build number still comes after channel priority.

The following command adds the channel "new_channel" to the top
of the channel list, making it the highest priority:

.. code-block:: shell

   conda config --add channels new_channel

Conda has an equivalent command:

.. code-block:: shell

   conda config --prepend channels new_channel

Conda also has a command that adds the new channel to the
bottom of the channel list, making it the lowest priority:

.. code-block:: shell

   conda config --append channels new_channel

.. _strict:
.. _channel-best-practices:

Channel configuration best practices
====================================

To avoid channel conflicts and ensure environment reproducibility,
we recommend the following approach:

1. **Use a single channel as your default.** Configure either
   ``defaults`` or ``conda-forge`` in your ``.condarc``, but not both.
   Mixing these channels in your global configuration can result in
   mixed-channel environments with incompatible packages and can
   introduce hard-to-debug dependency conflicts.

2. **Install from a specific channel with a single command when needed.** If you
   need a package from a channel that isn't in your global config,
   you can target that channel with a single command using the options below.
   Note that mixing packages from different channels in this way might result in
   dependency issues if the channels are not fully compatible.

   * The ``--channel`` flag installs the named package and all its
     dependencies from the specified channel. Add ``--override-channels``
     to ignore any channels configured in your ``.condarc``,
     using only the specified channel.

     .. code-block:: shell

         conda install --channel conda-forge --override-channels numpy

   * The ``<channel>::<package>`` syntax installs only the named
     package from the specified channel, with dependencies resolved
     from your configured channels.

     .. warning::

        If the channel you specify and your configured channels are not
        fully compatible, this approach can result in binary
        incompatibilities that can cause hard-to-debug runtime errors,
        also known as "ABI incompatibility".

     .. code-block:: shell

         conda install conda-forge::numpy

3. **Use strict channel priority only if you must mix channels.**
   If your workflow requires both ``defaults`` and ``conda-forge`` in
   your channel list, set your channel priority to ``strict``
   to reduce the risk of incompatible mixed-channel environments:

   .. code-block:: shell

      conda config --set channel_priority strict

   .. warning::

      Strict channel priority can make some environments unsatisfiable.
      It also prevents fallback to lower-priority channels when a package
      with the same name exists in a higher-priority channel. This includes
      channels that supply packages not available as conda packages.

.. _`default channel`: https://repo.anaconda.com/pkgs/
