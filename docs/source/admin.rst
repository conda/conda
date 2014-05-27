========================================================================
 Administrative channel management for a centralized conda installation
========================================================================

By default, conda (and all packages it installs, including Anaconda) installs
locally with a user-specific configuration. No administrative privileges are
required, and no upstream files or other users are affected by the
installation.

However, it is also possible to install conda (and packages) in an
admin-controlled location that a group of users have access to. In this
configuration, each user may use the central conda installation with a
personalized configuration specified by a .condarc file located in their $HOME
directory. This user configuration is governed by a "root" .condarc file
located in the top-level conda installation directory given by ``$PREFIX``
(precisely, the path returned by ``sys.prefix``).

The administrative ``.condarc`` may specify a set of allowed channels as well
as the (optional) boolean flag ``allow_other_channels``. If
``allow_other_channels`` is set to true or not specified, each user will have
access to the channels specified in their local ``.condarc`` file (or the
default channels if none are specified at all). If ``allow_other_channels`` is
set to ``false``, only those channels explicitly specified in the
administrative ``.condarc`` file are allowed. If the user specifies other
channels, they will be blocked and the user will receive a message explaining
this.

To illustrate the usage and syntax, look at the following example. The first
command shows you that the administrative ``.condarc`` file is located in the
top-level conda installation directory. Here, the administrative ``.condarc``
file restricts allowed channels and specifies only a channel called "admin"
(this will also restrict access to the default channels because the "defaults"
channel is not explicitly specified)::

   $ which conda
   /tmp/miniconda/bin/conda

   $ more /tmp/miniconda/.condarc
   allow_other_channels : false
   channels:
     - admin

The user's ``.condarc`` file specifies only the default channels::

   $ more ~/.condarc
   channels:
     - defaults

which is reflected in the information conda displays to the user::

   $ conda info
   Current conda install:

                platform : osx-64
           conda version : 3.4.2
          python version : 3.3.5.final.0
        root environment : /tmp/miniconda  (read only)
     default environment : /tmp/miniconda
        envs directories : /Users/gergely/envs
                           /tmp/miniconda/envs
           package cache : /Users/gergely/envs/.pkgs
                           /tmp/miniconda/pkgs
            channel URLs : http://repo.continuum.io/pkgs/free/osx-64/
                           http://repo.continuum.io/pkgs/pro/osx-64/
             config file : /Users/gergely/.condarc
       is foreign system : False

However, because all channels are blocked except for "admin", the user will
receive this kind of message when seeking a package that is not available on
the restricted channels::

   $ conda search flask
   Fetching package metadata:
   Error: URL 'http://repo.continuum.io/pkgs/pro/osx-64/' not in allowed channels.

   Allowed channels are:
     - https://conda.binstar.org/admin/osx-64/

The user now knows they must add the "admin" channel to their local
``.condarc`` to access allowed packages.
