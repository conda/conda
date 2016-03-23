.. conda documentation master file, created by
   sphinx-quickstart on Sat Nov  3 16:08:12 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

=====
Conda
=====

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
