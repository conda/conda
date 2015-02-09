=================
 Troubleshooting
=================

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

Resolution: For C libraries, unset the environment variables ``LD_LIBRARY_PATH`` on Linux and ``DYLD_LIBRARY_PATH`` on Mac OS X.
--------------------------------------------------------------------------------------------------------------------------------

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

Issue: ``ValueError unknown locale: UTF-8`` on Mac OS X
=======================================================

Resolution: Uncheck "set locale environment variables on startup" setting in Terminal settings
----------------------------------------------------------------------------------------------

This is a bug in the OS X Terminal app that only shows up in certain locales
(country/language combinations). Open Terminal in /Applications/Utilities and
uncheck the box "Set locale environment variables on startup".

.. image:: locale.jpg

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
