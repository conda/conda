============================================
Using the .condarc conda configuration file
============================================

.. contents::
   :local:
   :depth: 2


.. _config-overview:

Overview
========

The conda configuration file, ``.condarc``, is an optional
runtime configuration file that allows advanced users to
configure various aspects of conda, such as which channels it
searches for packages, proxy settings and environment
directories.

The ``.condarc`` file is not included by default, but it is
automatically created in your home directory the first time you
run the ``conda config`` command.

A ``.condarc`` file may also be located in the root environment,
in which case it overrides any in the home directory.

NOTE: A ``.condarc`` file can also be used in an
administrator-controlled installation to override the users’
configuration. See :doc:`admin-multi-user-install`.

The ``.condarc`` configuration file follows simple
`YAML syntax <http://docs.ansible.com/YAMLSyntax.html>`_.

The ``.condarc`` file can change many parameters, including:

* Where conda looks for packages.

* If and how conda uses a proxy server.

* Where conda lists known environments.

* Whether to update the bash prompt with the current activated
  environment name.

* Whether user-built packages should be uploaded to
  `Anaconda.org <http://anaconda.org>`_.

* Default packages or features to include in new environments.

To create or modify a ``.condarc`` file, use
the ``conda config`` command or use a text editor to create a
new file named ``.condarc`` and save it to your user home
directory or root directory.

EXAMPLE:

.. code-block:: yaml

  conda config --add channels conda-forge

You can also download a :doc:`sample .condarc file
<sample-condarc>` to edit in your editor and save to your user
home directory or root directory.

To set configuration options, edit the ``.condarc`` file directly
or use the ``conda config --set`` command.

EXAMPLE: To set the auto_update_conda option to ``False``, run::

  conda config --set auto_update_conda False

For a complete list of conda config commands, see the
`command reference <../../commands/conda-config>`. The same list
is available at the Terminal or Anaconda Prompt by running
``conda config --help``.

TIP: Conda supports :doc:`tab completion <enable-tab-completion>`
with external packages instead of internal configuration.

For more information, see the `Configuration section of Advanced
Features of conda Part 1
<http://continuum.io/blog/advanced-conda-part-1#configuration>`_.


General configuration
=====================

.. _config-channels:

Channel locations (channels)
----------------------------

Listing channel locations in the ``.condarc`` file overrides
conda defaults, causing conda to search only the channels listed
here, in the order given.

Use ``defaults`` to automatically include all default channels.
Non-URL channels are interpreted as Anaconda.org user names. You
can change this by modifying the channel_alias as described
in :ref:`set-ch-alias`. The default is just ``defaults``.

EXAMPLE:

.. code-block:: yaml

  channels:
    - <anaconda_dot_org_username>
    - http://some.custom/channel
    - file:///some/local/directory
    - defaults

To select channels for a single environment, put a ``.condarc``
file in the root directory of that environment.

EXAMPLE: If you have installed Miniconda with Python 3 in your
home directory and the environment is named "flowers", the
path may be::

  ~/miniconda3/envs/flowers/.condarc


Allow other channels (allow_other_channels)
-------------------------------------------

The system-level ``.condarc`` file may specify a set of allowed
channels, and it may allow users to install packages from other
channels with the boolean flag allow_other_channels. The default
is ``True``.

If allow_other_channels is set to ``False``, only those channels
explicitly specified in the system ``.condarc`` file are allowed:

.. code-block:: yaml

  allow_other_channels: False

When allow_other_channels is set to ``True`` or not specified,
each user has access to the default channels and to any channels
that the user specifies in their local ``.condarc`` file. When
allow_other_channels is set to ``false``, if the user specifies
other channels, the other channels are blocked, and the user
receives a message reporting that channels are blocked. For more
information, see :ref:`admin-inst`.

If the system ``.condarc`` file specifies a channel_alias,
it overrides any channel aliases set in a user's ``.condarc``
file. See :ref:`channel-alias`.

Default channels (default_channels)
-----------------------------------

Normally the default repository is `repo.continuum.io
<http:repo.continuum.io>`_, but if default_channels is defined,
it sets the new list of default channels. This is especially
useful for air gap and enterprise installations:

.. code-block:: yaml

  channels:
    - <anaconda_dot_org_username>
    - http://some.custom/channel
    - file:///some/local/directory
    - defaults

Update conda automatically (auto_update_conda)
----------------------------------------------

When ``True``, conda updates itself any time a user updates or
installs a package in the root environment. When ``False``,
conda updates itself only if the user manually issues a
``conda update`` command. The default is ``True``.

EXAMPLE:

.. code-block:: yaml

  auto_update_conda: False


Always yes (always_yes)
-----------------------

Choose the ``yes`` option whenever asked to proceed, such as
when installing. Same as using the ``--yes`` flag at the
command line. The default is ``False``.

EXAMPLE:

.. code-block:: yaml

  always_yes: True


Show channel URLs (show_channel_urls)
-------------------------------------

Show channel URLs when displaying what is going to be downloaded
and in ``conda list``. The default is ``False``.

EXAMPLE:

.. code-block:: yaml

  show_channel_urls: True


Change command prompt (changeps1)
---------------------------------

When using ``activate``, change the command prompt from ``$PS1``
to include the activated environment. The default is ``True``.

EXAMPLE:

.. code-block:: yaml

  changeps1: False


Add pip as Python dependency (add_pip_as_python_dependency)
-----------------------------------------------------------

Add pip, wheel and setuptools as dependencies of Python. This
ensures that pip, wheel and setuptools are always installed any
time Python is installed. The default is ``True``.

EXAMPLE:

.. code-block:: yaml

  add_pip_as_python_dependency: False


Use pip (use_pip)
-----------------

Use pip when listing packages with ``conda list``. This does not
affect any conda command or functionality other than the output
of the command ``conda list``. The default is ``True``.

EXAMPLE:

.. code-block:: yaml

  use_pip: False


.. _config-proxy:

Configure conda for use behind a proxy server (proxy_servers)
-------------------------------------------------------------

By default, proxy settings are pulled from the HTTP_PROXY and
HTTPS_PROXY environment variables or the system. Setting them
here overrides that default:

.. code-block:: yaml

  proxy_servers:
      http: http://user:pass@corp.com:8080
      https: https://user:pass@corp.com:8080

To give a proxy for a specific scheme and host, use the
scheme://hostname form for the key. This matches for any request
to the given scheme and exact host name:

.. code-block:: yaml

  proxy_servers:
    'http://10.20.1.128': 'http://10.10.1.10:5323'

If you do not include the user name and password or if
authentication fails, conda prompts for a user name and password.

If your password contains special characters, you need escape
them as described in `Percent-encoding reserved characters
<https://en.wikipedia.org/wiki/Percent-encoding#Percent-encoding_reserved_characters>`_ ,
on Wikipedia.

Be careful not to use ``http`` when you mean https or
``https`` when you mean http.


.. _SSL_verification:

SSL verification (ssl_verify)
-----------------------------

If you are behind a proxy that does SSL inspection such as a
Cisco IronPort Web Security Appliance (WSA), you may need to use
ssl_verify to override the SSL verification settings.

By default this variable is ``True``, which means that SSL
verification is used and conda verifies certificates for SSL
connections. Setting this variable to ``False`` disables the
connection's normal security and is not recommended:

.. code-block:: yaml

  ssl_verify: False

You can also set ssl_verify to a string path to a certificate,
which can be used to verify SSL connections:

.. code-block:: yaml

  ssl_verify: corp.crt


Offline mode only (offline)
---------------------------

Filters out all channel URLs that do not use the ``file://``
protocol. The default is ``False``.

EXAMPLE:

.. code-block:: yaml

  offline: True


Advanced configuration
======================


Disallow soft-linking (allow_softlinks)
---------------------------------------

When allow_softlinks is ``True``, conda uses hard-links when
possible and soft-links---symlinks---when hard-links are not
possible, such as when installing on a different file system
than the one that the package cache is on.

When allow_softlinks is ``False``, conda still uses
hard-links when possible, but when it is not possible, conda
copies files. Individual packages can override this option,
specifying that certain files should never be soft-linked. See
:ref:`no-link`.

The default is ``True``.

EXAMPLE:

.. code-block:: yaml

  allow_softlinks: False


.. _set-ch-alias:

.. _channel-alias:

Set a channel alias (channel_alias)
-----------------------------------

Whenever you use the ``-c`` or ``--channel`` flag to give conda a
channel name that is not a URL, conda prepends the channel_alias
to the name that it was given. The default channel_alias is
https://conda.anaconda.org/.

EXAMPLE: The command::

  conda install --channel asmeurer <package>

is the same as::

  conda install --channel https://conda.anaconda.org/asmeurer <package>

You can set channel_alias to your own repository.

EXAMPLE: To set channel_alias to your repository at
https://yourrepo.com:

.. code-block:: yaml

  channel_alias: https://your.repo/

On Windows, you must include a slash ("/") at the end of the URL:

EXAMPLE: https://your.repo/conda/

When channel_alias set to your repository at
https://yourrepo.com::

  conda install --channel jsmith <package>

is the same as::

  conda install --channel https://yourrepo.com/jsmith <package>


.. _config-add-default-pkgs:

Always add packages by default (create_default_packages)
--------------------------------------------------------

When creating new environments, add the specified packages by
default. The default packages are installed in every environment
you create. You can override this option at the command prompt
with the ``--no-default-packages`` flag. The default is to not
include any packages.

EXAMPLE:

.. code-block:: yaml

  create_default_packages:
    - pip
    - ipython
    - scipy=0.15.0


Track features (track_features)
-------------------------------

Enable certain features to be tracked by default. The default is
to not track any features. This is similar to adding mkl to
the create_default_packages list.

EXAMPLE:

.. code-block:: yaml

  track_features:
    - mkl

Disable updating of dependencies (update_dependencies)
------------------------------------------------------

By default, ``conda install`` updates the given package and all
its dependencies to the latest versions.

If you prefer to update only the packages given explicitly at
the command line and avoid updating existing installed packages
as much as possible, set update_dependencies to ``True``:

.. code-block:: yaml

   update_dependencies: True

NOTE: Conda still ensures that dependency specifications are
satisfied. Thus, some dependencies may still be updated or,
conversely, this may prevent packages given at the command line
from being updated to their latest versions. You can always
specify versions at the command line to force conda to install a
given version, such as ``conda install numpy=1.9.3``.

You can enable and disable this option
at the command line with the ``--update-dependencies`` and
``--no-update-dependencies`` flags.

To avoid updating only specific packages in an environment, a
better option may be to pin them. For more information, see
:ref:`pinning-packages`.


Disallow installation of specific packages (disallow)
-----------------------------------------------------

Disallow the installation of certain packages. The default is to
allow installation of all packages.

EXAMPLE:

.. code-block:: yaml

  disallow:
    - anaconda


Add Anaconda.org token to automatically see private packages (add_anaconda_token)
---------------------------------------------------------------------------------

When the channel alias is Anaconda.org or an Anaconda Server GUI,
you can set the system configuration so that users automatically
see private packages. Anaconda.org was formerly known as
binstar.org. This uses the Anaconda command-line client, which
you can install with ``conda install anaconda-client``, to
automatically add the token to the channel URLs.

The default is ``True``.

EXAMPLE:

.. code-block:: yaml

  add_anaconda_token: False

NOTE: Even when set to ``True``, this setting is enabled only if
the Anaconda command-line client is installed and you are
logged in with the ``anaconda login`` command.


Specify environment directories (envs_dirs)
-------------------------------------------

Specify directories in which environments are located. If this
key is set, the root prefix ``envs_dir`` is not used unless
explicitly included. This key also determines where the package
caches are located.

For each envs here, ``envs/pkgs`` is used as the pkgs cache,
except for the standard ``envs`` directory in the root
directory, for which the normal ``root_dir/pkgs`` is used.

EXAMPLE:

.. code-block:: yaml

  envs_dirs:
    - ~/my-envs
    - /opt/anaconda/envs

The CONDA_ENVS_PATH environment variable overwrites this setting:

* For macOS and Linux:
  ``CONDA_ENVS_PATH=~/my-envs:/opt/anaconda/envs``

* For Windows:
  ``set CONDA_ENVS_PATH=C:\Users\joe\envs;C:\Anaconda\envs``


Conda build configuration
=========================


Specify conda build output root directory (root-dir)
----------------------------------------------------

Build output root directory. You can also set this with the
CONDA_BLD_PATH environment variable. The default is
``<CONDA_PREFIX>/conda-bld/``. If you do not have write
permissions to ``<CONDA_PREFIX>/conda-bld/`` , the default is
``~/conda-bld/`` .

EXAMPLE:

.. code-block:: yaml

  conda-build:
      root-dir: ~/conda-builds


Automatically upload conda build packages to Anaconda.org (anaconda_upload)
---------------------------------------------------------------------------

Automatically upload packages built with conda build to
`Anaconda.org <http://anaconda.org>`_. The default is ``False``.

EXAMPLE:

.. code-block:: yaml

  anaconda_upload: True


Token to be used for Anaconda.org uploads (conda-build 3.0+) (anaconda_token)
-----------------------------------------------------------------------------

Tokens are a means of authenticating with anaconda.org without logging in.
You can pass your token to conda-build with this condarc setting, or with a CLI
argument.  This is unset by default.  Setting it implicitly enables
anaconda_upload.

  .. code-block:: yaml

     conda-build:
         anaconda_token: gobbledygook


Limit build output verbosity (conda-build 3.0+) (quiet)
-------------------------------------------------------

Conda-build's output verbosity can be reduced with the ``quiet`` setting. For
more verbosity use the CLI flag ``--debug``.

.. code-block:: yaml

   conda-build:
       quiet: true


Disable filename hashing (conda-build 3.0+) (filename_hashing)
--------------------------------------------------------------

Conda-build 3 adds hashes to filenames to allow greater customization of
dependency versions. If you find this disruptive, you can disable the hashing
with the following config entry:

.. code-block:: yaml

   conda-build:
       filename_hashing: false

NOTE: conda-build does no checking when clobbering packages. If you
utilize conda-build 3's build matrices with a build configuration that is not
reflected in the build string, packages will be missing due to clobbering.


Disable recipe and package verification (conda-build 3.0+) (no_verify)
----------------------------------------------------------------------

By default, conda-build uses conda-verify to ensure that your recipe and package
meet some minimum sanity checks.  You can disable these:

.. code-block:: yaml

   conda-build:
       no_verify: true


Disable per-build folder creation (conda-build 3.0+) (set_build_id)
-------------------------------------------------------------------

By default, conda-build creates a new folder for each build, named for the
package name plus a timestamp. This allows you to do multiple builds at once. If
you have issues with long paths, you may need to disable this behavior. You
should first try to change the build output root directory with the ``root-dir``
setting described above, but fall back to this as necessary:

.. code-block:: yaml

   conda-build:
       set_build_id: false


Skip building packages that already exist (conda-build 3.0+) (skip_existing)
----------------------------------------------------------------------------

By default, conda-build builds all recipes that you specify. You can instead
skip recipes that are already built. A recipe is skipped if and only if *all* of
its outputs are available on your currently configured channels.

.. code-block:: yaml

   conda-build:
       skip_existing: true


Omit recipe from package (conda-build 3.0+) (include_recipe)
------------------------------------------------------------

By default, conda-build includes the recipe that was used to build the package.
If this contains sensitive or proprietary information, you can omit the recipe.

.. code-block:: yaml

   conda-build:
       include_recipe: false

NOTE: If you do not include the recipe, you cannot use conda-build to test
the package after the build completes. This means that you cannot split your
build and test steps across two distinct CLI commands (``conda build --notest
recipe`` and ``conda build -t recipe``). If you need to omit the recipe and
split your steps, your only option is to remove the recipe files from the
tarball artifacts after your test step. Conda-build does not provide tools for
doing that.


Disable activation of environments during build/test (conda-build 3.0+) (activate)
----------------------------------------------------------------------------------

By default, conda-build activates the build and test environments prior to
executing the build or test scripts. This adds necessary PATH entries, and also
runs any activate.d scripts you may have. If you disable activation, the PATH
will still be modified, but the activate.d scripts will not run. This is not
recommended, but some people prefer this.

.. code-block:: yaml

   conda-build:
       activate: false


PyPI upload settings (conda-build 3.0+) (pypirc)
------------------------------------------------

Unset by default.  If you have wheel outputs in your recipe, conda-build will
try to upload them to the PyPI repository specified by the ``pypi_repository``
setting using credentials from this file path.

.. code-block:: yaml

   conda-build:
       pypirc: ~/.pypirc


PyPI repository to upload to (conda-build 3.0+) (pypi_repository)
-----------------------------------------------------------------

Unset by default.  If you have wheel outputs in your recipe, conda-build will
try to upload them to this PyPI repository using credentials from the file
specified by the ``pypirc`` setting.

.. code-block:: yaml

   conda-build:
       pypi_repository: pypi


Obtaining information from the .condarc file
==============================================

NOTE: It may be necessary to add the "force" option ``-f`` to
the following commands.

To get all keys and their values:

.. code-block:: bash

   conda config --get

To get the value of a specific key, such as channels:

.. code-block:: bash

   conda config --get channels

To add a new value, such as
http://conda.anaconda.org/mutirri, to a specific key, such as
channels:

.. code-block:: bash

   conda config --add channels http://conda.anaconda.org/mutirri

To remove an existing value, such as
http://conda.anaconda.org/mutirri from a specific key, such as
channels:

.. code-block:: bash

   conda config --remove channels http://conda.anaconda.org/mutirri

To remove a key, such as channels, and all of its values:

.. code-block:: bash

   conda config --remove-key channels

To configure channels and their priority for a single
environment, make a ``.condarc`` file in the :ref:`root directory
of that environment <config-channels>`.
