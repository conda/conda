.. conda documentation master file, created by
   sphinx-quickstart on Sat Nov  3 16:08:12 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

=====
Conda
=====

.. figure::  images/conda_logo.svg
   :align:   center

Conda is an open source package management system and environment management system for installing multiple
versions of software packages and their dependencies and switching easily between them. It works on
Linux, OS X and Windows, and was created for Python programs but can package and distribute any software.

Conda is included in Anaconda and Miniconda. Conda is also included in the Continuum `subscriptions <https://www.continuum.io/anaconda-subscriptions>`_
of Anaconda, which provide on-site enterprise package and environment management for Python, R, Node.js, Java, and other application
stacks. Conda is also available on pypi, although that approach may not be as up-to-date.

* Miniconda is a small “bootstrap” version that includes only conda and conda-build, and installs Python. Over 720
  scientific packages and their dependencies can be installed individually from the Continuum repository with
  the “conda install” command.
* Anaconda includes conda, conda-build, Python, and over 150 automatically installed scientific packages and
  their dependencies. As with Miniconda, over 250 additional scientific packages can be installed individually with
  the “conda install” command.
* pip install conda uses the released version on pypi.  This version allows you to create new conda environments using
  any python installation, and a new version of Python will then be installed into those environments.  These environments
  are still considered "Anaconda installations."

The `conda` command is the primary interface for managing `Anaconda
<http://docs.continuum.io/anaconda/index.html>`_ installations. It can query
and search the Anaconda package index and current Anaconda installation,
create new conda environments, and install and update packages into existing
conda environments.


.. raw:: html

        <iframe width="560" height="315" src="https://www.youtube.com/embed/UaIvrDWrIWM" frameborder="0" allowfullscreen></iframe>


.. toctree::
   :hidden:

   get-started
   using/index
   building/build
   help/help
   get-involved

Presentations & Blog Posts
--------------------------

`Packaging and Deployment with conda - Travis Oliphant <https://speakerdeck.com/teoliphant/packaging-and-deployment-with-conda>`_

`Python 3 support in Anaconda - Ilan Schnell <https://www.continuum.io/content/python-3-support-anaconda>`_

`New Advances in conda - Ilan Schnell <https://www.continuum.io/blog/developer/new-advances-conda>`_

`Python Packages and Environments with conda - Bryan Van de Ven <https://www.continuum.io/content/python-packages-and-environments-conda>`_

`Advanced features of Conda, part 1 - Aaron Meurer <https://www.continuum.io/blog/developer/advanced-features-conda-part-1>`_

`Advanced features of Conda, part 2 - Aaron Meurer <https://www.continuum.io/blog/developer/advanced-features-conda-part-2>`_

Requirements
------------

* python 2.7, 3.4, or 3.5
* pycosat
* pyyaml
* requests

What's new in conda 4.1.0?
--------------------------

This release contains many small bug fixes for all operating systems, and a few special fixes for Windows behavior. The `changelog <https://github.com/conda/conda/releases/tag/4.1.0>`_ contains a complete list of changes. 

**Windows-only changes include:**

* Shortcuts are no longer installed by default on Windows: Shortcuts can now be installed with the --shortcuts option. Example 1: Install a shortcut to Spyder with conda install spyder --shortcut Note if you have Anaconda (not Miniconda), you already have this shortcut and Spyder. Example 2: Install the open source package named console_shortcut. When you click the shortcut icon, a terminal window will open with the environment containing the console_shortcut package already activated. conda install console_shortcut --shortcuts
* Skip binary replacement on Windows: Linux & OS X have binaries that are coded with library locations, and this information must sometimes be replaced for relocatability, but Windows does not generally embed prefixes in binaries, and was already relocatable. We skip binary replacement on Windows.

**Notable changes for all systems Windows, OS X and Linux:**

* Channel order now matters. The most significant conda change is that when you add channels, channel order matters. If you have a list of channels in a .condarc file, conda installs the package from the first channel where it's available, even if it's available in a later channel with a higher version number.
* No version downgrades. Conda remove no longer performs version downgrades on any remaining packages that might be suggested to resolve dependency losses; the package will just be removed instead.
* New YAML parser/emitter. PyYAML is replaced with Ruamel.yaml, which gives more robust control over yaml document use. More info
* Script paths over 127 characters are now truncated  (Linux, OS X only). For each package in an environment, conda creates a script in that environment, and the first line of the script consists of “#!” and the path to that environment’s Python interpreter. When these lines were over 127 characters some errors were reported, so conda now checks the length and replaces long lines with "#! /usr/bin/env python", which uses the version of Python that comes first in the PATH variable. 
* Changes to conda list command. When looking for packages that aren’t installed with conda, conda list now examines the Python site-packages directory rather than relying on pip.
* Changes to conda remove. The command  'conda remove --all' now removes a conda environment without fetching information from a remote server on the packages in the environment.
* Conda update can be turned off and on. When turned off, conda will not update itself unless the user manually issues a conda update command. Previously conda updated any time a user updated or installed a package in the root environment. Use the option 'conda config set auto_update_conda false'.
* Improved support for BeeGFS, the parallel cluster file system for performance and designed for very easy installation and management.

See the `changelog <https://github.com/conda/conda/releases/tag/4.1.0>`_ for a complete list of changes. 


