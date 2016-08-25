=================
 Troubleshooting
=================

Table of contents:

#. :ref:`permission-denied`
#. :ref:`conda-claims-installed`
#. :ref:`DistributionNotFound`
#. :ref:`unknown-locale`
#. :ref:`AttributeError-getproxies`
#. :ref:`shell-command-location`
#. :ref:`wrong-python`
#. :ref:`unsatisfiable`
#. :ref:`version-from-channel`

.. _permission-denied:

Issue:  permission denied errors during install
===============================================

umask is a command that determines the mask settings that control how file permissions are set for newly created files. If you have a very restrictive umask (such as 077), you will see "permission denied" errors.

Resolution:  set less restrictive umask before calling conda commands.
----------------------------------------------------------------------

Conda was intended as a user space tool, but often users need to use it in a global environment. One place this can go awry is with restrictive file permissions.  Conda creates links when you install files that have to be read by others on the system.

To give yourself full permissions for files and directories, but prevent the group and other users from having access, before installing set the umask to 007, install conda, then return the umask to the original setting afterwards:

   .. code-block:: bash

      $ umask 007
      $ conda install
      $ umask 077


For more information on umask, please visit `http://en.wikipedia.org/wiki/Umask <http://en.wikipedia.org/wiki/Umask>`_.


.. _conda-claims-installed:

Issue: Conda claims that a package is installed, but it appears not to be.
==========================================================================

Sometimes conda will claim that a package is already installed, but it will
not appear to be, e.g., a Python package that gives ImportError.

There are a few possible causes of this issue:

Resolution: Make sure you are in the right conda environment.
-------------------------------------------------------------

``conda info`` will tell you what environment is currently active (under
"default environment"). You can verify that you are using the Python from the
correct environment by running

.. code:: python

   import sys
   print(sys.prefix)

Resolution: For Python packages, make sure you do not have ``PYTHONPATH`` or ``PYTHONHOME`` set.
------------------------------------------------------------------------------------------------

The command ``conda info -a`` will show you the values of these environment
variables.

These environment variables cause Python to load files from locations other
than the standard ones. Conda works best when these environment variables are
not set, as their typical use-cases are obviated by Conda environments, and a
common issue is that they will cause Python to pick up the wrong versions or
broken versions of a library.

To unset them temporarily for the current terminal session, run ``unset
PYTHONPATH``. To unset them permanently, check for lines in the files
``~/.bashrc``, ``~/.bash_profile``, ``~/.profile`` if you use bash,
``~/.zshrc`` if you use zsh, or the file output by ``$PROFILE`` if you use
PowerShell on Windows.

Resolution: For Python packages, remove any site-specific directories.
----------------------------------------------------------------------

Another possibility for Python are so-called site-specific files. These
typically live in ``~/.local`` on Unix. The full description of where
site-specific packages can be found is in `PEP 370
<http://legacy.python.org/dev/peps/pep-0370/>`_. As with ``PYTHONPATH``,
Python may try importing packages from this directory, which can cause
issues. The recommended fix is to remove the site-specific directory.

Resolution: For C libraries, unset the environment variables ``LD_LIBRARY_PATH`` on Linux and ``DYLD_LIBRARY_PATH`` on OS X.
----------------------------------------------------------------------------------------------------------------------------

These act similarly to ``PYTHONPATH`` for Python. If they are set, they can
cause libraries to be loaded from locations other than the Conda
environment. Again, Conda environments obviate most use-cases for these
variables, so it is recommended to unset them if they are set, unless you know
what you are doing. ``conda info -a`` will show what these are set to (on the
relevant operating system).

Resolution: Occasionally, an installed package will become corrupted.
---------------------------------------------------------------------

Conda works by unpacking the packages in the pkgs directory and then hard
linking them to the environment. Sometimes these get corrupted somehow,
breaking all environments that use them, and also any additional environments,
since the same files are hard linked each time.

**conda install -f will unarchive the package again and re-link it.** It also
does a md5 verification on the package (usually if this is different, it's
because your channels have changed and there is a different package with the
same name, version, and build number). Note that this breaks the links to any
other environments that already had this package installed, so you'll have to
reinstall it there too. It also means that running ``conda install -f`` a lot
can use up a lot of disk space if you have a lot of environments.  Note that
the ``-f`` flag to ``conda install`` (``--force``) implies ``--no-deps``, so
``conda install -f package`` will not reinstall any of the dependencies of
``package``.


.. _DistributionNotFound:

Issue: pkg_resources.DistributionNotFound: conda==3.6.1-6-gb31b0d4-dirty
========================================================================

Resolution: Force reinstall conda
---------------------------------

A useful way to work off the development version of conda is to run ``python
setup.py develop`` on a checkout of the `conda git repository
<https://github.com/conda/conda>`_.  However, if you are not regularly
running ``git pull``, it is a good idea to un-develop, as you will otherwise
not get any regular updates to conda.  The normal way to do this is to run
``python setup.py develop -u``.

However, this command does not replace the ``conda`` script itself. With other
packages, this is not an issue, as you can just reinstall them with ``conda``,
but conda cannot be used if conda is installed.

The fix is to use the ``./bin/conda`` executable in the conda git repository
to force reinstall conda, i.e., run ``./bin/conda install -f conda``.  You can
then verify with ``conda info`` that you have the latest version of conda, and
not a git checkout (the version should not include any hashes).


.. _unknown-locale:

Issue: ``ValueError unknown locale: UTF-8`` on OS X
===================================================

Resolution: Uncheck "set locale environment variables on startup" setting in Terminal settings
----------------------------------------------------------------------------------------------

This is a bug in the OS X Terminal app that only shows up in certain locales
(country/language combinations). Open Terminal in /Applications/Utilities and
uncheck the box "Set locale environment variables on startup".

.. image:: help/locale.jpg

This will set your ``LANG`` environment variable to be empty. This may cause
terminal use to incorrect settings for your locale. The ``locale`` command in
the Terminal will tell you what settings are used.  To use the correct
language, add a line to your bash profile (typically ``~/.profile``)

.. code-block:: bash

   export LANG=your-lang

Replace ``your-lang`` with the correct locale specifier for your language. The
command ``locale -a`` will show you all the specifiers. For example, the
language code for US English is ``en_US.UTF-8``. The locale affects what
translations are used when they are available, and also how dates,
currencies, and decimals are formatted.


.. _AttributeError-getproxies:

Issue: ``AttributeError`` or missing ``getproxies``
===================================================

When running a command such as ``conda update ipython``, you may get an
``AttributeError: 'module' object has no attribute 'getproxies'``.

Resolution: Update ``requests`` and be sure ``PYTHONPATH`` is not set.
----------------------------------------------------------------------

This can be caused by an old version of ``requests``, or by having the ``PYTHONPATH``
environment variable set.

``conda info -a`` will show the ``requests`` version and various environment
variables such as ``PYTHONPATH``.

The ``requests`` version can be updated with ``pip install -U requests``.

On Windows ``PYTHONPATH`` can be cleared in the environment variable settings.
On OS X and Linux it can typically be cleared by removing it from the bash
profile and restarting the shell.


.. _shell-command-location:

Issue:  Shell commands open from wrong location
===============================================

When I run a command within a conda environment, conda does not access the correct package executable.

Resolution:  Reactivate the environment or run ``hash -r`` (in bash) or ``rehash`` (in zsh)
-------------------------------------------------------------------------------------------

The way both bash and zsh work is that when you enter a command, the shell
searches the paths in ``PATH`` one by one until it finds the command. The shell
then caches the location (this is called "hashing" in shell terminology), so that
when you type the command again, the shell doesn't have to search the ``PATH``
again.

The problem is that before you conda installed the program, you ran the command
which loaded and hashed the one in some other location on the ``PATH`` (such as
``/usr/bin``). Then you installed the program using ``conda install``, but the
shell still had the old instance hashed.

When you run ``source activate``, conda automatically runs ``hash -r`` in bash and
``rehash`` in zsh to clear the hashed commands, so conda will find things in the
new path on the ``PATH``. But there is no way to do this when ``conda install``
is run (the command must be run inside the shell itself, meaning either you
have to type the command yourself or source a file that contains the command).

This is a relatively rare problem, since this will only happen if you activate
an environment or use the root environment, run a command from somewhere else,
then conda install a program and try to run the program again without running ``source
activate`` or ``source deactivate``.

The command ``type command_name`` will always tell you exactly what is being
run (this is better than ``which command_name``, which ignores hashed commands
and searches the ``PATH`` directly), and ``hash -r`` (in bash) or ``rehash``
(in zsh) will reset the hash, or you can run ``source activate``.


.. _wrong-python:

Issue:  Programs fail due to invoking conda Python and not system Python
========================================================================

After installing Anaconda or miniconda, programs that run ``python`` will switch
from invoking the system Python to invoking the Python in the root conda
environment. If these programs rely on the system Python to have certain
configurations or dependencies that are not in the root conda environment
Python, the programs may crash. For example, some users of the Cinnamon desktop
environment on Linux Mint have reported these crashes.

Resolution: Fix the ``PATH`` environment variable
-------------------------------------------------

Edit your ``.bash_profile`` and ``.bashrc`` files so that the conda binary
directory (such as ``~/miniconda3/bin``) is no longer added to the ``PATH``
environment variable. ``conda`` ``activate`` and ``deactivate`` may still be run
by using their full path names such as ``~/miniconda3/bin/conda``.

You may also create a folder with symbolic links to ``conda`` ``activate`` and
``deactivate``, and edit your ``.bash_profile`` or ``.bashrc`` file to add this
folder to your ``PATH``. Then running ``python`` will invoke the system Python,
but running ``conda`` commands, ``source activate MyEnv``, ``source activate root``,
or ``source deactivate`` will work normally.

After running ``source activate`` to activate any environment, including after
running ``source activate root``, running ``python`` will invoke the Python in
the active conda environment.


.. _unsatisfiable:

Issue: ``UnsatisfiableSpecifications`` error
============================================

Not all conda package installation specifications are possible to satisfy.

For example, ``conda create -n tmp python=3 wxpython=3`` produces an
Unsatisfiable Specifications error because wxPython 3 depends on Python 2.7, so
the specification to install Python 3 conflicts with the specification to
install wxPython 3.

Resolution: Fix the conflicts in the installation request
---------------------------------------------------------

When an unsatisfiable request is made to conda, conda shows a message such as
this one::

    The following specifications were found to be in conflict:
    - python 3*
    - wxpython 3* -> python 2.7*
    Use "conda info <package>" to see the dependencies for each package.

This indicates that the specification to install wxpython 3 depends on
installing Python 2.7, which conflicts with the specification to install python
3.

You can use "conda info wxpython" or "conda info wxpython=3" to show information
about this package and its dependencies::

    wxpython 3.0 py27_0
    -------------------
    file name   : wxpython-3.0-py27_0.tar.bz2
    name        : wxpython
    version     : 3.0
    build number: 0
    build string: py27_0
    channel     : defaults
    size        : 34.1 MB
    date        : 2014-01-10
    fn          : wxpython-3.0-py27_0.tar.bz2
    license_family: Other
    md5         : adc6285edfd29a28224c410a39d4bdad
    priority    : 2
    schannel    : defaults
    url         : https://repo.continuum.io/pkgs/free/osx-64/wxpython-3.0-py27_0.tar.bz2
    dependencies:
        python 2.7*
        python.app

By examining the dependencies of each package, you should be able to determine
why the installation request produced a conflict, and modify the request so it
can be satisfied without conflicts. In our example, we could install wxPython
with Python 2.7::

    conda create -n tmp python=2.7 wxpython=3

.. _version-from-channel:

Issue: install a specific version from channels
-----------------------------------------------

Suppose you have a specific need to install the Python ``cx_freeze`` module
with Python 3.4.  A first step is to create a Python 3.4 environment::

.. code-block:: bash

   conda create -n py34 python=3.4

Using this environment you should first attempt::

.. code-block:: bash

   conda install -n py34 cx_freeze

However, when you do this you'll get the following error (at the time this was written, on the platform used)::

   Using Anaconda Cloud api site https://api.anaconda.org
   Fetching package metadata .........
   Solving package specifications: .
   Error: Package missing in current osx-64 channels:
   - cx_freeze

   You can search for packages on anaconda.org with

     anaconda search -t conda cx_freeze

This is telling us that ``cx_freeze`` cannot be found, at least not in the *default* package channels. However there may be a community-created version available and if so we can search for it using exactly the command that is listed above.

.. code-block:: bash

   $ anaconda search -t conda cx_freeze
   Using Anaconda Cloud api site https://api.anaconda.org
   Run 'anaconda show <USER/PACKAGE>' to get more details:
   Packages:
        Name                      |  Version | Package Types   | Platforms
        ------------------------- |   ------ | --------------- | ---------------
        inso/cx_freeze            |    4.3.3 | conda           | linux-64
        pyzo/cx_freeze            |    4.3.3 | conda           | linux-64, win-32, win-64, linux-32, osx-64
                                             : http://cx-freeze.sourceforge.net/
        silg2/cx_freeze           |    4.3.4 | conda           | linux-64
                                             : create standalone executables from Python scripts
        takluyver/cx_freeze       |    4.3.3 | conda           | linux-64
   Found 4 packages

In this example, there are four different places we **could** try using to get
it. None of them are officially supported or endorsed by Continuum, but
members of the conda community have provided many valuable packages. If we
want to go with public opinion then `the web interface
<https://anaconda.org/search?q=cx_freeze>`_ provides more information:

.. figure:: images/package-popularity.png
   :alt: cx_freeze packages on anaconda.org

Notice that the ``pyzo`` organization has by far the most downloads, so you might
choose to use their package. If so, you can add their organization's channel
by specifying it on the command line (as shown below):

.. code-block:: bash

   $ conda create -c pyzo -n cxfreeze_py34 cx_freeze python=3.4
   Using Anaconda Cloud api site https://api.anaconda.org
   Fetching package metadata: ..........
   Solving package specifications: .........

   Package plan for installation in environment /Users/ijstokes/anaconda/envs/cxfreeze_py34:

   The following packages will be downloaded:

       package                    |            build
       ---------------------------|-----------------
       cx_freeze-4.3.3            |           py34_4         1.8 MB
       setuptools-20.7.0          |           py34_0         459 KB
       ------------------------------------------------------------
                                              Total:         2.3 MB

   The following NEW packages will be INSTALLED:

       cx_freeze:  4.3.3-py34_4
       openssl:    1.0.2h-0
       pip:        8.1.1-py34_1
       python:     3.4.4-0
       readline:   6.2-2
       setuptools: 20.7.0-py34_0
       sqlite:     3.9.2-0
       tk:         8.5.18-0
       wheel:      0.29.0-py34_0
       xz:         5.0.5-1
       zlib:       1.2.8-0

Now you have a software environment sandbox created with Python 3.4 and
``cx_freeze``.
