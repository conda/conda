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
Therefore, you can now safely put channels at the bottom of your
channel list to provide additional packages that are not in the
default channels and still be confident that these channels will
not override the core package set.

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

* Run the equivalent command::

    conda config --set channel_priority disabled

Conda then sorts as follows:

#. Sorts the package list from highest to lowest version number.

#. Sorts tied packages from highest to lowest channel priority.

#. Sorts tied packages from highest to lowest build number.

Because build numbers from different channels are not
comparable, build number still comes after channel priority.

The following command adds the channel "new_channel" to the top
of the channel list, making it the highest priority::

  conda config --add channels new_channel

Conda has an equivalent command::

  conda config --prepend channels new_channel

Conda also has a command that adds the new channel to the
bottom of the channel list, making it the lowest priority::

  conda config --append channels new_channel

.. _strict:

Strict channel priority
=======================

As of version 4.6.0, Conda has a strict channel priority feature.
Strict channel priority can dramatically speed up conda operations and
also reduce package incompatibility problems. We recommend setting channel
priority to "strict" when possible.

Details about it can be seen by typing ``conda config --describe channel_priority``.

.. code-block:: none

    channel_priority (ChannelPriority)
    Accepts values of 'strict', 'flexible', and 'disabled'. The default
    value is 'flexible'. With strict channel priority, packages in lower
    priority channels are not considered if a package with the same name
    appears in a higher priority channel. With flexible channel priority,
    the solver may reach into lower priority channels to fulfill
    dependencies, rather than raising an unsatisfiable error. With channel
    priority disabled, package version takes precedence, and the
    configured priority of channels is used only to break ties. In
    previous versions of conda, this parameter was configured as either
    True or False. True is now an alias to 'flexible'.

    channel_priority: flexible

.. _`default channel`: https://repo.anaconda.com/pkgs/
