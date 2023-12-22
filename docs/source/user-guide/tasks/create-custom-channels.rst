========================
Creating custom channels
========================

In this tutorial, we walk through how to create your own channel
that either be access via the local or network file system or served
from a webserver.

To create a custom channel:

#. You will need to install conda-build to complete this tutorial. If you do not already have it,
   you can install it with the following command:

   .. code::

      conda install conda-build

#. Organize all the packages in subdirectories for the platforms you wish to serve. Below
   is an example of what this may look like:

   .. code::

      channel
      ├── linux-64
      │   └── package-1.0-0.tar.bz2
      ├── osx-64
      │   └── package-1.0-0.tar.bz2
      └── win-64
          └── package-1.0-0.tar.bz2

#. Run ``conda index`` on the channel root directory:

   .. code::

      conda index channel/

   The conda index command generates a file ``repodata.json``,
   saved to each repository directory, which conda uses to get
   the metadata for the packages in the channel.

   .. note::
      Each time you add or modify a package in the channel,
      you must rerun ``conda index`` for conda to see the update.

#. To test custom channels, serve the custom channel using a web
   server or using a ``file://`` URL to the channel directory.
   Test by sending a search command to the custom channel.

   **Example**: if you want a file in the custom channel location
   ``/opt/channel/linux-64/``, search for files in that location:

   .. code::

      conda search -c file:///opt/channel/ --override-channels

   .. note::
      * The channel URL does not include the platform, as conda
        automatically detects and adds the platform.
      * The option  ``--override-channels`` ensures that conda
        searches only your specified channel and no other channels,
        such as default channels or any other channels you may have
        listed in your ``.condarc`` file.

   If you have set up your private repository correctly, you
   get the following output:

   .. code::

      Fetching package metadata: . . . .

   This is followed by a list of the conda packages found. This
   verifies that you have set up and indexed your private
   repository successfully.
