========
Settings
========

This page contains an overview of many important settings available in conda
with examples where possible.

General configuration
=====================

.. _config-channels:

Channel locations (``channels``)
--------------------------------

Listing channel locations in the ``.condarc`` file overrides
conda defaults, causing conda to search only the channels listed there
in the order given.

Use ``defaults`` to automatically include all default channels.
Non-URL channels are interpreted as Anaconda.org user or organization
names. You can change this by modifying the ``channel_alias`` as described
in :ref:`set-ch-alias`. The default is just ``defaults``.

**Example:**

.. code-block:: yaml

  channels:
    - <anaconda_dot_org_username>
    - http://some.custom/channel
    - file:///some/local/directory
    - defaults

To select channels for a single environment, put a ``.condarc``
file in the root directory of that environment (or use the
``--env`` option when using ``conda config``).

**Example:** If you have installed Miniconda with Python 3 in your
home directory and the environment is named "flowers", the
path may be::

  ~/miniconda3/envs/flowers/.condarc

.. _default-channels:

Default channels (``default_channels``)
---------------------------------------

Normally, the defaults channel points to several channels at the
`repo.anaconda.com <https://repo.anaconda.com/>`_ repository, but if
``default_channels`` is defined, it sets the new list of default channels.
This is especially useful for airgapped and enterprise installations.

To ensure that all users only pull packages from an on-premises
repository, an administrator can set both :ref:`channel alias <channel-alias>` and
``default_channels``.

.. code-block:: yaml

  default_channels:
    - http://some.custom/channel
    - file:///some/local/directory

.. _auto-update-conda:

Update conda automatically (``auto_update_conda``)
--------------------------------------------------

When ``True``, conda updates itself any time a user updates or
installs a package in the root environment. When ``False``,
conda updates itself only if the user manually issues a
``conda update`` command. The default is ``True``.

**Example:**

.. code-block:: yaml

  auto_update_conda: False

.. _always-yes:

Always yes (``always_yes``)
---------------------------

Choose the ``yes`` option whenever asked to proceed, such as
when installing. Same as using the ``--yes`` flag at the
command line. The default is ``False``.

**Example:**

.. code-block:: yaml

  always_yes: True

.. _show-channel-urls:

Show channel URLs (``show_channel_urls``)
-----------------------------------------

Show channel URLs in ``conda list`` and when displaying what is
going to be downloaded. The default is ``False``.

**Example:**

.. code-block:: yaml

  show_channel_urls: True

.. _change-command-prompt:

Change command prompt (``changeps1``)
-------------------------------------

When using ``conda activate``, change the command prompt from ``$PS1``
to include the activated environment. The default is ``True``.

**Example:**

.. code-block:: yaml

  changeps1: False

.. _add-pip-python-dependency:

Add pip as Python dependency (``add_pip_as_python_dependency``)
---------------------------------------------------------------

Add pip, wheel, and setuptools as dependencies of Python. This
ensures that pip, wheel, and setuptools are always installed any
time Python is installed. The default is ``True``.

**Example:**

.. code-block:: yaml

  add_pip_as_python_dependency: False

.. _use-pip:

Use pip (``use_pip``)
---------------------

Use pip when listing packages with ``conda list``. This does not
affect any conda command or functionality other than the output
of the command ``conda list``. The default is ``True``.

**Example:**

.. code-block:: yaml

  use_pip: False

.. _config-proxy:

Configure conda for use behind a proxy server (``proxy_servers``)
-----------------------------------------------------------------

By default, proxy settings are pulled from the HTTP_PROXY and
HTTPS_PROXY environment variables or the system. Setting them
here overrides that default:

.. code-block:: yaml

  proxy_servers:
      http: http://user:pass@corp.com:8080
      https: https://user:pass@corp.com:8080

To give a proxy for a specific scheme and host, use the
``scheme://hostname`` form for the key. This matches for any request
to the given scheme and exact host name:

.. code-block:: yaml

  proxy_servers:
    'http://10.20.1.128': 'http://10.10.1.10:5323'

If you do not include the username and password or if
authentication fails, conda prompts for a username and password.

If your password contains special characters, you need to escape
them as described in `Percent-encoding reserved characters
<https://en.wikipedia.org/wiki/Percent-encoding#Percent-encoding_reserved_characters>`_
on Wikipedia.

Be careful not to use ``http`` when you mean ``https`` or
``https`` when you mean ``http``.


.. _SSL_verification:

SSL verification (``ssl_verify``)
---------------------------------

If you are behind a proxy that does SSL inspection, such as a
Cisco IronPort Web Security Appliance (WSA), you may need to use
``ssl_verify`` to override the SSL verification settings.

By default, this variable is ``True``, which means that SSL
verification is used and conda verifies certificates for SSL
connections. Setting this variable to ``False`` disables the
connection's normal security and is not recommended:

.. code-block:: yaml

  ssl_verify: False

You can also set ``ssl_verify`` to a string path to a certificate,
which can be used to verify SSL connections:

.. code-block:: yaml

  ssl_verify: corp.crt

.. _offline-mode-only:

Offline mode only (``offline``)
-------------------------------

Filters out all channel URLs that do not use the ``file://``
protocol. The default is ``False``.

**Example:**

.. code-block:: yaml

  offline: True

Advanced configuration
======================

.. _disallow-soft-linking:

Disallow soft-linking (``allow_softlinks``)
-------------------------------------------

When ``allow_softlinks`` is ``True``, conda uses hard links when
possible and soft links (symlinks) when hard links are not
possible, such as when installing on a different file system
than the one that the package cache is on.

When ``allow_softlinks`` is ``False``, conda still uses
hard links when possible, but when it is not possible, conda
copies files. Individual packages can override this option,
specifying that certain files should never be soft linked.

The default is ``True``.

**Example:**

.. code-block:: yaml

  allow_softlinks: False

.. _set-ch-alias:

.. _channel-alias:

Set a channel alias (``channel_alias``)
---------------------------------------

Whenever you use the ``-c`` or ``--channel`` flag to give conda a
channel name that is not a URL, conda prepends the ``channel_alias``
to the name that it was given. The default ``channel_alias`` is
https://conda.anaconda.org.

If ``channel_alias`` is set
to ``https://my.anaconda.repo:8080/conda/``, then a user who runs the
command ``conda install -c conda-forge some-package`` will install the
package some-package from ``https://my.anaconda.repo:8080/conda/conda-forge``.

For example, the command::

  conda install --channel asmeurer <package>

is the same as::

  conda install --channel https://conda.anaconda.org/asmeurer <package>

You can set ``channel_alias`` to your own repository.

**Example:** To set ``channel_alias`` to your repository at
https://your.repo.com:

.. code-block:: yaml

  channel_alias: https://your.repo/

On Windows, you must include a slash ("/") at the end of the URL:

**Example:** https://your.repo/conda/

When ``channel_alias`` set to your repository at
https://your.repo.com::

  conda install --channel jsmith <package>

is the same as::

  conda install --channel https://your.repo.com/jsmith <package>

.. _config-add-default-pkgs:

Always add packages by default (``create_default_packages``)
------------------------------------------------------------

When creating new environments, add the specified packages by
default. The default packages are installed in every environment
you create. You can override this option at the command prompt
with the ``--no-default-packages`` flag. The default is to not
include any packages.

**Example:**

.. code-block:: yaml

  create_default_packages:
    - pip
    - ipython
    - scipy=0.15.0

.. _track-features:

Track features (``track_features``)
-----------------------------------

Enable certain features to be tracked by default. The default is
to not track any features. This is similar to adding MKL to
the ``create_default_packages`` list.

**Example:**

.. code-block:: yaml

  track_features:
    - mkl

.. _disable-updating:

Disable updating of dependencies (``update_dependencies``)
----------------------------------------------------------

By default, ``conda install`` updates the given package to the
latest version and installs any dependencies necessary for
that package. However, if dependencies that satisfy the package's
requirements are already installed, conda will not update those
packages to the latest version.

In this case, if you would prefer that conda update all dependencies
to the latest version that is compatible with the environment,
set ``update_dependencies`` to ``True``.

The default is ``False``.

**Example:**

.. code-block:: yaml

   update_dependencies: True

.. note::

   Conda still ensures that dependency specifications are
   satisfied. Thus, some dependencies may still be updated or,
   conversely, this may prevent packages given at the command line
   from being updated to their latest versions. You can always
   specify versions at the command line to force conda to install a
   given version, such as ``conda install numpy=1.9.3``.

To avoid updating only specific packages in an environment, a
better option may be to pin them. For more information, see
:ref:`pinning-packages`.

.. _disallow-install:

Disallow installation of specific packages (``disallow``)
---------------------------------------------------------

Disallow the installation of certain packages. The default is to
allow installation of all packages.

**Example:**

.. code-block:: yaml

  disallow:
    - anaconda

.. _add-anaconda-token:

Add Anaconda.org token to automatically see private packages (``add_anaconda_token``)
-------------------------------------------------------------------------------------

When the channel alias is Anaconda.org or an Anaconda Server GUI,
you can set the system configuration so that users automatically
see private packages. Anaconda.org was formerly known as
binstar.org. This uses the Anaconda command-line client, which
you can install with ``conda install anaconda-client``, to
automatically add the token to the channel URLs.

The default is ``True``.

**Example:**

.. code-block:: yaml

  add_anaconda_token: False

.. note::

   Even when set to ``True``, this setting is enabled only if
   the Anaconda command-line client is installed and you are
   logged in with the ``anaconda login`` command.

.. _specify-env-directories:

Specify environment directories (``envs_dirs``)
-----------------------------------------------

Specify directories in which environments are located. If this
key is set, the root prefix ``envs_dir`` is not used unless
explicitly included. This key also determines where the package
caches are located.

For each envs here, ``envs/pkgs`` is used as the pkgs cache,
except for the standard ``envs`` directory in the root
directory, for which the normal ``root_dir/pkgs`` is used.

**Example:**

.. code-block:: yaml

  envs_dirs:
    - ~/my-envs
    - /opt/anaconda/envs

The ``CONDA_ENVS_PATH`` environment variable overwrites the ``envs_dirs`` setting:

* For macOS and Linux:
  ``CONDA_ENVS_PATH=~/my-envs:/opt/anaconda/envs``

* For Windows:
  ``set CONDA_ENVS_PATH=C:\Users\joe\envs;C:\Anaconda\envs``

.. _specify-pkg-directories:

Specify package directories (``pkgs_dirs``)
-------------------------------------------

Specify directories in which packages are located. If this
key is set, the root prefix ``pkgs_dirs`` is not used unless
explicitly included.

If the ``pkgs_dirs`` key is not set, then ``envs/pkgs`` is used
as the pkgs cache, except for the standard ``envs`` directory in the root
directory, for which the normal ``root_dir/pkgs`` is used.

**Example:**

.. code-block:: yaml

  pkgs_dirs:
    - /opt/anaconda/pkgs

The ``CONDA_PKGS_DIRS`` environment variable overwrites the
``pkgs_dirs`` setting:

* For macOS and Linux:
  ``CONDA_PKGS_DIRS=/opt/anaconda/pkgs``

* For Windows:
  ``set CONDA_PKGS_DIRS=C:\Anaconda\pkgs``

.. _use-only-tar-bz2:

Force conda to download only .tar.bz2 packages (``use_only_tar_bz2``)
---------------------------------------------------------------------

Conda 4.7 introduced a new ``.conda`` package file format.
``.conda`` is a more compact and faster alternative to ``.tar.bz2`` packages.
It's thus the preferred file format to use where available.

Nevertheless, it's possible to force conda to only download ``.tar.bz2`` packages
by setting the ``use_only_tar_bz2`` boolean to ``True``.

The default is ``False``.

**Example:**

.. code-block:: yaml

  use_only_tar_bz2: True

.. note::

   This is forced to ``True`` if conda-build is installed and older than 3.18.3,
   because older versions of conda break when conda feeds it the new file format.

Conda-build configuration
=========================

.. _specify-root-dir:

Specify conda-build output root directory (``root-dir``)
--------------------------------------------------------

Build output root directory. You can also set this with the
``CONDA_BLD_PATH`` environment variable. The default is
``<CONDA_PREFIX>/conda-bld/``. If you do not have write
permissions to ``<CONDA_PREFIX>/conda-bld/``, the default is
``~/conda-bld/``.

**Example:**

.. code-block:: yaml

  conda-build:
      root-dir: ~/conda-builds
.. _specify-output-folder:

Specify conda-build build folder (conda-build 3.16.3+) (``output_folder``)
--------------------------------------------------------------------------

Folder to dump output package to. Packages are moved here if build or test
succeeds. If unset, the output folder corresponds to the same directory as
the root build directory (``root-dir``).

.. code-block:: yaml

   conda-build:
       output_folder: conda-bld

.. _pkg_format:

Specify conda-build package version (``pkg_version``)
-----------------------------------------------------

Conda package version to create. Use ``2`` for ``.conda`` packages. If not set, conda-build defaults to ``.tar.bz2``.

.. code-block:: yaml

   conda-build:
      pkg_format: 2

.. _auto-upload:

Automatically upload conda-build packages to Anaconda.org (``anaconda_upload``)
-------------------------------------------------------------------------------

Automatically upload packages built with conda-build to
`Anaconda.org <http://anaconda.org>`_. The default is ``False``.

**Example:**

.. code-block:: yaml

  anaconda_upload: True

.. _anaconda-token:

Token to be used for Anaconda.org uploads (conda-build 3.0+) (``anaconda_token``)
---------------------------------------------------------------------------------

Tokens are a means of authenticating with Anaconda.org without logging in.
You can pass your token to conda-build with this ``.condarc`` setting, or with a CLI
argument. This is unset by default. Setting it implicitly enables
``anaconda_upload``.

.. code-block:: yaml

   conda-build:
       anaconda_token: gobbledygook

.. _quiet:

Limit build output verbosity (conda-build 3.0+) (``quiet``)
-----------------------------------------------------------

Conda-build's output verbosity can be reduced with the ``quiet`` setting. For
more verbosity, use the CLI flag ``--debug``.

.. code-block:: yaml

   conda-build:
       quiet: true

.. _filename-hashing:

Disable filename hashing (conda-build 3.0+) (``filename_hashing``)
------------------------------------------------------------------

Conda-build 3 adds hashes to filenames to allow greater customization of
dependency versions. If you find this disruptive, you can disable the hashing
with the following config entry:

.. code-block:: yaml

   conda-build:
       filename_hashing: false

.. warning::

   Conda-build does not check when clobbering packages. If you
   utilize conda-build 3's build matrices with a build configuration that is not
   reflected in the build string, packages will be missing due to clobbering.

.. _no-verify:

Disable recipe and package verification (conda-build 3.0+) (``no_verify``)
--------------------------------------------------------------------------

By default, conda-build uses conda-verify to ensure that your recipe
and package meet some minimum sanity checks. You can disable these:

.. code-block:: yaml

   conda-build:
       no_verify: true

.. _set-build-id:

Disable per-build folder creation (conda-build 3.0+) (``set_build_id``)
-----------------------------------------------------------------------

By default, conda-build creates a new folder for each build, named for the
package name plus a timestamp. This allows you to do multiple builds at once.
If you have issues with long paths, you may need to disable this behavior.
You should first try to change the build output root directory with the
``root-dir`` setting described above, but fall back to this as necessary:

.. code-block:: yaml

   conda-build:
       set_build_id: false

.. _skip-existing:

Skip building packages that already exist (conda-build 3.0+) (``skip_existing``)
--------------------------------------------------------------------------------

By default, conda-build builds all recipes that you specify. You can instead
skip recipes that are already built. A recipe is skipped if and only if *all* of
its outputs are available on your currently configured channels.

.. code-block:: yaml

   conda-build:
       skip_existing: true

.. _include-recipe:

Omit recipe from package (conda-build 3.0+) (``include_recipe``)
----------------------------------------------------------------

By default, conda-build includes the recipe that was used to build the package.
If this contains sensitive or proprietary information, you can omit the recipe.

.. code-block:: yaml

   conda-build:
       include_recipe: false

.. note::

   If you do not include the recipe, you cannot use conda-build to test
   the package after the build completes. This means that you cannot split your
   build and test steps across two distinct CLI commands (``conda build --notest
   recipe`` and ``conda build -t recipe``). If you need to omit the recipe and
   split your steps, your only option is to remove the recipe files from the
   tarball artifacts after your test step. Conda-build does not provide tools for
   doing that.

.. _disable-activation:

Disable activation of environments during build/test (conda-build 3.0+) (``activate``)
--------------------------------------------------------------------------------------

By default, conda-build activates the build and test environments prior to
executing the build or test scripts. This adds necessary PATH entries, and also
runs any activate.d scripts you may have. If you disable activation, the PATH
will still be modified, but the activate.d scripts will not run. This is not
recommended, but some people prefer this.

.. code-block:: yaml

   conda-build:
       activate: false

.. _long-test-prefix:

Disable long prefix during test (conda-build 3.16.3+) (``long_test_prefix``)
----------------------------------------------------------------------------

By default, conda-build uses a long prefix for the test prefix. If you have recipes
that fail in long prefixes but would still like to test them in short prefixes, you
can disable the long test prefix. This is not recommended.

.. code-block:: yaml

   conda-build:
       long_test_prefix: false

The default is ``true``.

.. _pypi-upload-settings:

PyPI upload settings (conda-build 3.0+) (``pypirc``)
----------------------------------------------------

Unset by default. If you have wheel outputs in your recipe, conda-build will
try to upload them to the PyPI repository specified by the ``pypi_repository``
setting using credentials from this file path.

.. code-block:: yaml

   conda-build:
       pypirc: ~/.pypirc

.. _pypi-repository:

PyPI repository to upload to (conda-build 3.0+) (``pypi_repository``)
---------------------------------------------------------------------

Unset by default. If you have wheel outputs in your recipe, conda-build will
try to upload them to this PyPI repository using credentials from the file
specified by the ``pypirc`` setting.

.. code-block:: yaml

   conda-build:
       pypi_repository: pypi

Expansion of environment variables
==================================

Conda expands environment variables in a subset of configuration settings.
These are:

- ``channel``
- ``channel_alias``
- ``channels``
- ``client_cert_key``
- ``client_cert``
- ``custom_channels``
- ``custom_multichannels``
- ``default_channels``
- ``envs_dirs``
- ``envs_path``
- ``migrated_custom_channels``
- ``pkgs_dirs``
- ``proxy_servers``
- ``verify_ssl``
- ``allowlist_channels``

This allows you to store the credentials of a private repository in an
environment variable, like so:

.. code-block:: yaml

  channels:
    - https://${USERNAME}:${PASSWORD}@my.private.conda.channel
.. _threads:

Configuring number of threads
=============================

You can use your ``.condarc`` file or environment variables to
add configuration to control the number of threads. You may
want to do this to tweak conda to better utilize your system.
If you have a very fast SSD, you might increase the number
of threads to shorten the time it takes for conda to create
environments and install/remove packages.

``repodata_threads``
--------------------

* Default number of threads: None
* Threads used when downloading, parsing, and creating repodata
  structures from ``repodata.json`` files. Multiple downloads from
  different channels may occur simultaneously. This speeds up the
  time it takes to start solving.

``verify_threads``
------------------

* Default number of threads: 1
* Threads used when verifying the integrity of packages and files
  to be installed in your environment. Defaults to 1, as using
  multiple threads here can run into problems with slower hard
  drives.

``execute_threads``
-------------------

* Default number of threads: 1
* Threads used to unlink, remove, link, or copy files into your
  environment. Defaults to 1, as using multiple threads here can
  run into problems with slower hard drives.

``default_threads``
-------------------

* Default number of threads: None
* When set, this value is used for all of the above thread
  settings. With its default setting (None), it does not affect
  the other settings.

Setting any of the above can be done in ``.condarc`` or with
conda config:

At your terminal::

  conda config --set repodata_threads 2

In ``.condarc``::

  verify_threads: 4
