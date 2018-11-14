=================
Managing channels
=================

Different channels can have the same package, so conda must handle these
channel collisions.

There will be no channel collisions if you use only the defaults channel.
There will also be no channel collisions if all of the channels you use only
contain packages that do not exist in any of the other channels in your list.
The way conda resolves these collisions matters only when you have multiple
channels in your channel list that host the same package.


Before conda 4.1.0
==================

Before conda 4.1.0 was released on June 14, 2016, when two channels 
hosted packages with the same name, conda installed the package 
with the highest version number. If there were two packages 
with the same version number, conda installed the one with the 
highest build number. Only if both the version numbers and build 
numbers were identical did the channel ordering make a 
difference. This approach had 3 problems:

* Build numbers from different channels are not comparable. 
  Channel A could do nightly builds while Channel B does weekly 
  builds, so build 2 from Channel B could be newer than build 4 
  from Channel A.

* Users could not specify a preferred channel. You might consider 
  Channel B more reliable than Channel A and prefer to get 
  packages from that channel even if the B version is older than 
  the package in Channel A. Conda provided no way to choose that 
  behavior. Only version and build numbers mattered.

* Build numbers conflicted. This is an effect of the other 2 
  problems. Assume you were happily using package Alpha from 
  Channel A and package Bravo from Channel B. The provider from 
  Channel B then added a version of Alpha with a very high build 
  number. Your conda updates would start installing new versions 
  of Alpha from Channel B whether you wanted that or not. This 
  could cause unintentional problems and a risk of deliberate 
  attacks.


After conda 4.1.0
=================

By default, conda now prefers packages from a higher priority 
channel over any version from a lower priority channel. 
Therefore, you can now safely put channels at the bottom of your 
channel list to provide additional packages that are not in the 
default channels, and still be confident that these channels will 
not override the core package set.

Conda collects all of the packages with the same name across all 
listed channels and processes them as follows:

#. Sorts packages from highest to lowest channel priority.

#. Sorts tied packages---same channel priority---from highest to 
   lowest version number.

#. Sorts still-tied packages---same channel priority and same 
   version---from highest to lowest build number.

#. Installs the first package on the sorted list that satisfies 
   the installation specifications.

To make conda use the old method and install the newest version 
of a package in any listed channel:

* Add ``channel_priority: false`` to your ``.condarc`` file. 

  OR

* Run the equivalent command:: 
  
    conda config --set channel_priority false

Conda then sorts as follows: 

#. Sorts the package list from highest to lowest version number.

#. Sorts tied packages from highest to lowest channel priority.

#. Sorts tied packages from highest to lowest build number. 

Because build numbers from different channels are not 
comparable, build number still comes after channel priority.

The following command adds the channel "new_channel" to the top 
of the channel list, making it the highest priority::

  conda config --add channels new_channel

Conda now has an equivalent command::

  conda config --prepend channels new_channel

Conda also now has a command that adds the new channel to the 
bottom of the channel list, making it the lowest priority::

  conda config --append channels new_channel
