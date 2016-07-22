=======================
Managing conda channels
=======================

It is possible for different channels to have the same package, so conda must 
handle these channel collisions. If you only use the defaults channel, or only 
use channels that only contain packages that do not exist in any of the other 
channels in your list, there will be no channel collisions. The way conda 
resolves these collisions only matters when you have multiple channels in your 
channel list that host the same package.

Before conda 4.1.0
==================

Before conda 4.1.0 was released on June 14th, 2016, when two channels hosted 
packages with the same name, conda would install the package with the highest 
version number. If there were two packages with the same version number, conda 
would install the one with the highest build number. Only if both the version 
numbers and build numbers were identical did your channel ordering make a 
difference. This had three problems.

1. *Build numbers from different channels are not comparable.* Channel A could 
   do nightly builds while Channel B does weekly builds, so build 2 from Channel 
   B could be newer than build 4 from Channel A.

2. *Users could not specify a preferred channel.* You might consider Channel B 
   more reliable than Channel A and prefer to get packages from that channel 
   even if the version is older than the package in Channel A. Before version 
   4.1.0 conda provided no way to choose that behavior. Only version and build 
   numbers mattered.

3. *Build number conflicts.* This is an effect of the other two problems. If you 
   were happily using package Alpha from Channel A and package Bravo from 
   Channel B, and the provider from Channel B then added a version of Alpha to 
   Channel B with a very high build number, your conda updates would start 
   installing new versions of Alpha from Channel B whether you wanted that or 
   not. This could cause both unintentional problems and a risk of deliberate 
   attacks.

After conda 4.1.0
=================

By default conda now prefers packages from a higher priority channel over any 
version from a lower priority channel. Therefore you can now safely put channels 
at the bottom of your channel list to provide additional packages that are not 
in the default channels, and still be confident that these channels will not 
override the core package set.

By default conda collects all of the packages with the same name across all 
listed channels and sorts them from highest to lowest channel priority, then 
sorts packages that are tied from highest to lowest version number, then sorts 
packages that are still tied from highest to lowest build number, and then 
installs the first package on the sorted list that satisfies the installation 
specifications.

To make conda use the old method and install the newest version of a package in 
any listed channel, add ``channel_priority: false`` to your .condarc file. (You 
may instead run the equivalent 
command ``conda config --set channel_priority false``.) Then conda will sort the 
package list from highest to lowest version number, then sort tied packages from 
highest to lowest channel priority, and then sort tied packages from highest to 
lowest build number. Because build numbers from different channels are not 
comparable, build number still comes after channel priority.

The command ``conda config --add channels new_channel`` adds the new channel to 
the top of the channel list, making it the highest priority. Conda now has an 
equivalent command ``conda config --prepend channels new_channel``. Conda also 
now has a new command ``conda config --append channels new_channel`` that puts 
the new channel at the bottom of the channel list, making it the lowest 
priority.
