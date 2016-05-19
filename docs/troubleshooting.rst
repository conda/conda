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
