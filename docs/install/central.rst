========================================================================
Centralized installation
========================================================================

.. contents::

Overview
========

Administrators who wish to restrict what programs users can install may do so with a system configuration file,
or .condarc that follows the simple `YAML syntax <http://docs.ansible.com/YAMLSyntax.html>`_. The system
configuration file overrides any  .condarc configuration files installed by the user.

By default, conda and all packages it installs, including Anaconda, are installed locally with a user-specific
configuration. Administrative privileges are not required, and no upstream files or other users are affected by
the installation.

An administrator may make conda and any number of packages available to a group of one or more users, while
still preventing these users from installing unwanted packages with conda. To do this, the administrator installs
conda and the packages, if any, in a location that is controlled by the administrator and accessible by the users.

Each user may then use the central conda installation, which will read settings from their own "user" .condarc configuration file
located in their home directory. The users' configuration is limited by the second "system" .condarc
file, and the path to it is the same as the root environment prefix displayed by ``conda info``, as shown in the :ref:`admin-inst`
below.

The system configuration settings are commonly used in a system configuration file, although they may also be used in a
user configuration file.  All user configuration settings may also be used in a system configuration file.

See also: :doc:`Conda configuration file </config>`.

System configuration settings
=============================

Allow other channels (allow_other_channels)
-------------------------------------------

The administrative system configuration .condarc may specify a set of allowed channels, and may allow the
users to install packages from other channels with the boolean flag allow_other_channels.  The default is
True.

If allow_other_channels is set to false, only those channels explicitly specified in the administrative
.condarc file are allowed:

.. code-block:: yaml

  allow_other_channels: False

When set to true or not specified, then each user will have access to the default channels and to any
channels that the user specifies in their local .condarc file. If the user specifies other channels, the
other channels will be blocked and the user will receive a message explaining this. See example below.

If the system .condarc  file specifies a channel_alias, it will override any channel aliases set in users'
.condarc  files. See channel alias below.

Default channels (default_channels)
-----------------------------------

Normally the default repository is repo.continuum.io, but if default_channels is 
defined it will set the new list of default channels. This is especially useful 
for air gap and enterprise installations.

.. code-block:: yaml

  channels:
    - <anaconda_dot_org_username>
    - http://some.custom/channel
    - file:///some/local/directory
    - defaults

.. _SSL_verification:

SSL verification (ssl_verify)
-----------------------------

If you are behind a proxy that does SSL inspection such as a Cisco IronPort Web Security Appliance (WSA), 
it may be necessary to override the SSL verification settings using ``ssl_verify``.

By default this variable is ``True``, ssl verification is used and conda verifies 
certificates for SSL connections. The variable can be set to ``False``, but this 
disables the connection's normal security and is not recommended.

.. code-block:: yaml

  ssl_verify: False

``ssl_verify`` can also be set to a string path to a certificate to be used to verify SSL connections.

.. code-block:: yaml

  ssl_verify: corp.crt

Offline mode only (offline)
---------------------------

Offline mode filters out all channels URLs which do not start with ``file:``. The default is False.

.. code-block:: yaml

  offline: True

Channel alias (channel_alias)
-----------------------------

Alias for non-url channels used with the -c or --channel flag. The default is ``https://conda.anaconda.org/``

.. code-block:: yaml

  channel_alias: https://your.repo/

Disallow installation of specific packages (disallow)
-----------------------------------------------------

Package specifications to disallow installing. The default is to allow all packages.

.. code-block:: yaml

  disallow:
    - anaconda

Add Anaconda.org token to automatically see private packages (add_anaconda_token)
---------------------------------------------------------------------------------

When the channel alias is Anaconda.org or an Anaconda Server GUI, the system configuration file can be set so users
automatically see private packages. (Anaconda.org was formerly known as binstar.org.)
This uses the anaconda command line client (which can be installed with ``conda
install anaconda-client``) to automatically add the token to the channel urls.

The default is True.

.. code-block:: yaml

  add_anaconda_token: False

NOTE: Even when set to True, this is enabled only if the anaconda command line client is installed and you 
are logged in with the ``anaconda login`` command.

Specify environment directories (envs_dirs)
-------------------------------------------

Specify directories in which environments are located. If this key is set, the root prefix envs_dir is not used
unless explicitly included. This key also determines where the package caches will be located.

For each ``envs`` here, ``envs/pkgs`` will be used as the pkgs cache, except for the standard envs directory
in the root directory, for which the normal ``root_dir/pkgs`` is used. The ``CONDA_ENVS_PATH`` environment
variable will overwrite this configuration file setting.

.. code-block:: yaml

  envs_dirs:
    - ~/my-envs
    - /opt/anaconda/envs


* **Linux, OS X:** ``CONDA_ENVS_PATH=~/my-envs:/opt/anaconda/envs``
* **Windows:** ``set CONDA_ENVS_PATH=C:\Users\joe\envs;C:\Anaconda\envs``

.. _admin-inst:

Example admin-controlled installation
=====================================

In the following example, we take a look at the system configuration file, review the settings,
compare it to the user's configuration file, and see what happens when the user attempts to access a
file from a channel that is blocked. We then show how the user must modify their configuration file to
access the channels allowed by the administrator.

**System configuration file**

The system configuration file must be located in the top-level conda installation directory. So first we
check to see the path where conda is located:

.. code-block:: bash

  which conda
  /tmp/miniconda/bin/conda

Now we can look at the contents of the .condarc file located in the administrator's directory:

.. code-block:: bash

  cat /tmp/miniconda/.condarc

This administrative .condarc file sets allow_other_channels to false, and specifies that users may
download packages from only the 'admin' channel:

.. code-block:: none

  cat /tmp/miniconda/.condarc
  allow_other_channels : false
  channel_alias: https://conda.anaconda.org/
  channels:
    - admin

Because ``allow_other_channels`` is false and the channel 'defaults' are not explicitly specified, users
are disallowed from downloading packages from the default channels. We will check this in the next step.

Note: The admin channel can also be expressed as https://conda.anaconda.org/admin/

**User configuration file**

Let's check to see where the user's conda install is located:

.. code-block:: bash

  conda info
  Current conda install:
  . . .
         channel URLs : http://repo.continuum.io/pkgs/free/osx-64/
                        http://repo.continuum.io/pkgs/pro/osx-64/
          config file : /Users/gergely/.condarc

The 'conda info' command shows us that conda is using the user's .condarc file, located at
``/Users/gergely/.condarc`` and that the default channels such as ``repo.continuum.io`` are
listed as channel URLs.

Now let's look at the contents of the administrative .condarc file located in that directory:

.. code-block:: none

  cat ~/.condarc
  channels:
    - defaults

This user's .condarc file specifies only the default channels.

But the administrator config file has blocked default channels by specifying that only "admin" is
allowed. If this user attempts to search for  a package in the default channels, they will see a
message telling them what channels are allowed:

.. code-block:: bash

   conda search flask
   Fetching package metadata:
   Error: URL 'http://repo.continuum.io/pkgs/pro/osx-64/' not in allowed channels.
   Allowed channels are:
    - https://conda.anaconda.org/admin/osx-64/

This error message tells the user to add the "admin" channel to their configuration file.

Conclusion: The user must edit their local .condarc configuration file to access the package
through the admin channel:

.. code-block:: yaml

  channels:
    - admin

Now the user can search for packages in the allowed admin channel.
