=============================================
Administering a multi-user conda installation
=============================================

By default, conda and all packages it installs, including
Anaconda, are installed locally with a user-specific
configuration. Administrative privileges are not required, and
no upstream files or other users are affected by
the installation.

You can make conda and any number of packages available to a
group of one or more users, while preventing these users
from installing unwanted packages with conda:

#. Install conda and the allowed packages, if any, in a
   location that is under administrator control and
   accessible to users.

#. Create a
   :doc:`.condarc system configuration file <use-condarc>` in
   the appropriate folder for your operating system.
   This system-level configuration file will override any
   user-level configuration files installed by the user.

Each user accesses the central conda installation, which reads
settings from the user ``.condarc`` configuration file located
in their home directory. The path to the user file is the same
as the root environment prefix displayed by ``conda info``,
as shown in :ref:`admin-inst-user` below. The user
``.condarc`` file is limited by the system ``.condarc`` file.

System configuration settings are commonly used in a
system ``.condarc`` file but may also be used in a
user ``.condarc`` file. All user configuration settings may
also be used in a system ``.condarc`` file.

For information about settings in the ``.condarc`` file,
see :doc:`use-condarc`.

.. _admin-inst:

Example administrator-controlled installation
=============================================

The following example describes how to view the system
configuration file, review the settings, compare it to a user's
configuration file, and determine what happens when the user
attempts to access a file from a blocked channel. It then
describes how the user must modify their configuration file to
access the channels allowed by the administrator.

.. _system_config_location:

System configuration file
-------------------------

#. The system configuration file should be in the system conda directory,
   which is installation-invariant, and varies by operating system:

   - **Windows**: ``C:/ProgramData/conda/.condarc``
   - **All others**: ``/etc/conda/.condarc``

   Configuration files at the above paths will affect all installations
   of conda on the machine.  Other possible paths that you may place
   the .condarc file can be seen :ref:`here <_condarc_search_precedence>`.

   If you want to configure individual installations of conda,
   place the .condarc file inside the base environment directory of the
   installation.  This is not recommended for securely administering
   multi-user installations as enforcement of `#!final` parameters
   is unreliable.

#. View the contents of the ``.condarc`` file in the
   administrator's directory:

   .. code-block:: bash

      cat /tmp/miniconda/.condarc

   The following administrative ``.condarc`` file
   uses the ``#!final`` flag to specify the channels,
   default channels, and channel_alias available to the user.

   .. code-block:: bash

     $ cat /tmp/miniconda/.condarc

     channels:                                   #!final
       - admin

     channel_alias: https://conda.anaconda.org/  #!final

The ``#!final`` flag is very similar to the ``!important``
rule in CSS; any parameter within the ``.condarc`` that is
trailed by the ``#!final`` cannot be overwritten by any other
``.condarc`` source. For more information on this flag, see the
`Anaconda Blog <https://www.anaconda.com/blog/conda-configuration-engine-power-users>`_
on the subject.

Because the ``#!final`` flag has been used and the channel
defaults are not explicitly specified, users are disallowed
from downloading packages from the default channels. You can
check this in the next procedure.

.. _admin-inst-user:

User configuration file
-----------------------

#. Check the location of the user's conda installation:

   .. code-block:: bash

     $ conda info
     Current conda install:
     . . .
            channel URLs : https://repo.anaconda.com/pkgs/free/osx-64/
                           https://repo.anaconda.com/pkgs/pro/osx-64/
            config file : /Users/username/.condarc

   The ``conda info`` command shows that conda is using the
   user's ``.condarc`` file, located at
   ``/Users/username/.condarc`` and that the default channels
   such as ``repo.anaconda.com`` are listed as channel URLs.

#. View the contents of the administrative ``.condarc`` file in
   the directory that was located in step 1:

   .. code-block:: bash

     $ cat ~/.condarc
     channels:
       - defaults

   This user's ``.condarc`` file specifies only the default
   channels, but the administrator config file has blocked
   default channels by specifying that only ``admin`` is
   allowed. If this user attempts to search for a package in the
   default channels, they get a message telling them what
   channels are allowed:

   .. code-block:: bash

      $ conda search flask
      Fetching package metadata:
      Error: URL 'http://repo.anaconda.com/pkgs/pro/osx-64/' not
      in allowed channels.
      Allowed channels are:
       - https://conda.anaconda.org/admin/osx-64/

   This error message tells the user to add the ``admin`` channel
   to their configuration file.

#. The user must edit their local ``.condarc`` configuration file
   to access the package through the admin channel:

   .. code-block:: yaml

     channels:
       - admin

   The user can now search for packages in the allowed
   ``admin`` channel.
