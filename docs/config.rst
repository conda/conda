=============
Configuration
=============

.. contents::


The conda configuration file (.condarc)
=======================================

The conda configuration file  (.condarc) is an OPTIONAL runtime configuration
file which allows advanced users to configure various aspects of conda, such as which
channels it searches for packages, proxy settings, environment directories, etc.

A .condarc file is not included by default, but it is automatically created in
the user’s home directory when you use the ``conda config`` command.

A .condarc file may also be located in the root environment, in which case it
overrides any in the home directory.

Note: A .condarc file can also be used in an administrator-controlled
installation to override the users’ configuration. Please see :doc:`install/central`.

The conda configuration file can be used to change:

- Where conda looks for packages

- If and how conda uses a proxy server

- Where conda lists known environments

- Whether to update the bash prompt with the current activated environment name

- Whether user-built packages should be uploaded to Anaconda.org

- Default packages or features to include in new environments

- And more.

To create or modify a .condarc configuration file, from the command line, use
the ``conda config`` command, or use a text editor to create a new file named
.condarc and save to your user home directory or root directory.

The .condarc configuration file follows
simple `YAML syntax <http://docs.ansible.com/YAMLSyntax.html>`_.

:doc:`Download a sample .condarc file<install/sample-condarc>`.

Conda supports :doc:`tab completion<install/tab-completion>` with external packages
instead of internal configuration.

For more configuration information see: http://continuum.io/blog/advanced-conda-part-1#configuration


General configuration
=====================


Channel locations (channels)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Listing channel locations in the .condarc file will override conda defaults,
causing conda to search only the channels listed here, in the order given.

Use ``defaults`` to automatically include all default channels. Non-url channels
will be interpreted as Anaconda.org usernames, and this can be changed by modifying
the ``channel_alias`` key as explained below. The default is just ``defaults``.

.. code-block:: yaml

  channels:
    - <anaconda_dot_org_username>
    - http://some.custom/channel
    - file:///some/local/directory
    - defaults


Always yes (always_yes)
^^^^^^^^^^^^^^^^^^^^^^^

Choose the yes option whenever asked to proceed, such as when installing. Same
as using the ``--yes`` flag at the command line. The default is ``False``.

.. code-block:: yaml

  always_yes: True


Show Channel URLs (show_channel_urls)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Show channel URLs when displaying what is going to be downloaded and
in ``conda list``. The default is ``False``.

.. code-block:: yaml

  show_channel_urls: True


Change command prompt (changeps1)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When using ``activate``, change the command prompt (``$PS1``) to include the activated
environment. The default is ``True``.

.. code-block:: yaml

  changeps1: False


Use PIP (use_pip)
^^^^^^^^^^^^^^^^^

Use pip when listing packages with ``conda list``. Note that this does not affect
any conda command or functionality other than the output of the
command ``conda list``. The default is ``True``.

.. code-block:: yaml

  use_pip: False


Configure conda for use behind a proxy server (proxy_servers)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

By default, proxy settings are pulled from the ``HTTP_PROXY`` and ``HTTPS_PROXY``
environment variables or the system. Setting them here overrides that default.

.. code-block:: yaml

  proxy_servers:
      http: http://user:pass@corp.com:8080
      https: https://user:pass@corp.com:8080

Note: If you do not include the username and password, of if authentication
fails, conda will prompt for a username and password.

Note: If your password contains special characters they will need to be escaped
as follows: https://en.wikipedia.org/wiki/Percent-encoding#Percent-encoding_reserved_characters

Note: Be careful not to use ``http`` when you mean ``https``, or ``https`` when you mean ``http``.

Note: If you are behind a proxy that does SSL inspection such as a Cisco IronPort Web Security Appliance (WSA), 
it may be necessary to override the SSL verification settings using ``ssl_verify`` as described in :ref:`SSL_verification`.


Offline mode only (offline)
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Filters out all channels URLs which do not use the ``file://`` protocol. The
default is ``False``.

.. code-block:: yaml

  offline: True


Advanced configuration
======================


Disallow soft-linking (allow_softlinks)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When ``allow_softlinks`` is ``True``, conda uses hard-links when possible, and soft-links
(symlinks) when hard-links are not possible, such as when installing on a
different filesystem than the one that the package cache is on.

When ``allow_softlinks`` is ``False``, conda still uses hard-links when possible, but when it is
not possible, conda copies files. Note that individual packages can override
this, specifying that certain files should never be soft-linked, independent of
this option (see the ``no_link`` option in the build recipe documentation).

The default is ``True``.

.. code-block:: yaml

  allow_softlinks: False


Set a channel alias (channel_alias)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

By default, ``conda install --channel asmeurer <package>`` is the same
as ``conda install --channel https://conda.anaconda.org/asmeurer <package>``. This
is because the default ``channel_alias`` is https://conda.anaconda.org/ . Whenever
conda is given a channel name that is not a URL, it prepends the ``channel_alias``
to the front of the name it was given.

You can set the ``channel_alias`` to your own repository. If your repository is at
https://yourrepo.com then ``conda install --channel jsmith <package>`` would be
the same as ``conda install --channel https://yourrepo.com/jsmith <package>`` .

.. code-block:: yaml

  channel_alias: https://your.repo/


Always add packages by default (create_default_packages)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When creating new environments add these packages by default. You can override
this option at the command prompt with the ``--no-default-packages`` flag. The
default is not to include any packages.

.. code-block:: yaml

  create_default_packages:
    - ipython


Track features (track_features)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Enable certain features to be tracked by default. The default is to not track
any features. This is similar to adding ``mkl`` to the ``create_default_packages``
list.

.. code-block:: yaml

  track_features:
    - mkl

Disable updating of dependencies (update_dependencies)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

By default, ``conda install`` updates the given package and all its
dependencies to the latest versions.

If you prefer to only update the packages given explicitly at the command line
and avoid updating existing installed packages as much as possible, you can
set ``update_dependencies`` to ``True``.

.. code-block:: yaml

   update_dependencies: True

Note that conda will still ensure that dependency specifications are
satisfied, so some dependencies may still be updated, or, conversely, this may
prevent packages given at the command line from being updated to their latest
versions. You can always specify versions at the command line to force conda
to install a given version (like ``conda
install numpy=1.9.3``).

This option can also be enabled or disabled at the command line with the
``--update-dependencies`` and ``--no-update-dependencies`` flags.

To avoid updating only specific packages in an environment, a better option
may be to *pin* them. See :ref:`pinning-packages` for more information.

Conda build configuration
=========================


Automatically upload conda build packages to Anaconda.org (anaconda_upload)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Automatically upload packages built with ``conda build`` to Anaconda.org. The
default is ``False``.

.. code-block:: yaml

  anaconda_upload: True


Specify conda build output root directory (conda-build)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Build output root directory. This can also be set with the ``CONDA_BLD_PATH``
environment variable. The default is ``<CONDA_PREFIX>/conda-bld/``, or if you do
not have write permissions to ``<CONDA_PREFIX>/conda-bld/`` , ``~/conda-bld/`` .

.. code-block:: yaml

  conda-build:
      root-dir: ~/conda-builds


.. toctree::
   :hidden:

   install/sample-condarc
   install/tab-completion
