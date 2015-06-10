=================
 Custom channels
=================


Channels are the path that conda takes to look for packages, and the easiest
way to use and manage custom channels is to use a private or public repository
on `Anaconda.org <https://anaconda.org/>`_, formerly known as Binstar.org.   If 
you designate your Anaconda.org repository as private, then only you, and those 
you grant access, can access your private repository. 

If you do not wish to upload your packages to the internet, however, you can 
build a custom repository served either through a web server, or locally 
using a ``file://`` url.  


Custom channel/private repository summary
-----------------------------------------

#. Organize packages into platform subdirectories.
#. Run conda index on each of the platform subdirectories.
#. Test custom channels.


1. Organize packages into platform subdirectories
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To create a custom channel, first organize all the packages in subdirectories for 
the platforms you wish to serve.

Example: 

.. code::

   channel/
  linux-64/
     package-1.0-0.tar.bz2
  linux-32/
     package-1.0-0.tar.bz2
  osx-64/
     package-1.0-0.tar.bz2
  win-64/
     package-1.0-0.tar.bz2
  win-32/
     package-1.0-0.tar.bz2


2. Run conda index on each of the platform subdirectories
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ‘conda index’ command is part of the conda-build package. If you have not yet used 
conda build, begin by installing conda build:

.. code::

   conda install conda-build

Now run conda index on each of the platform subdirectories as shown:

.. code::

   conda index channel/linux-64 channel/osx-64

The conda index command generates a file ``repodata.json``, saved to each repository directory, 
which conda uses to get the metadata for the packages in the channel. 

Note: Each time you add or modify a package in the channel, you must re-run ``conda index`` for 
conda to see the update.


3. Test custom channels
~~~~~~~~~~~~~~~~~~~~~~~

You can now serve the custom channel using a web server, or using a ``file:// url`` to the channel 
directory. Test by sending a search command to the custom channel.

Example: if a file you want from the custom channel location is located at ``/opt/channel/linux-64/``

Then search for files in that location as shown:
  
.. code::

   conda search -c file://opt/channel/ --override-channels

Note: The channel url does NOT include the platform, as conda will automatically detect and add 
the platform. 

Note: the --override-channels is to be sure conda only searches your specified channel and no 
other channels, such as default channels or any other channels you may have listed in your ``.condarc`` 
file.

If you have set up your private repository correctly, you will see:

.. code::

   Fetching package metadata: . . . .

This will be followed by a list of the conda packages found.
This verifies that you have set up and indexed your private repository successfully. 


