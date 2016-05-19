==================
Using R with conda
==================

For Linux, OS X and Windows

If you have conda installed, you can easily install R and over 80 of the most used R packages for data science with one command. Conda helps you keep your packages and dependencies up to date. You can also easily create and share your own custom R packages.

R-Essentials works very much like Anaconda:

* Installs all of the most popular packages with all of their dependencies with one command: ``conda install -c r r-essentials``
* Update all of the packages and their dependencies with one command: ``conda update -c r r-essentials``
* Update a single package in R-Essentials (if a new version of  the package is available in the R channel) with the command ``conda update r-XXXX``

How to install "R Essentials"
=============================

1. `Download and install Anaconda <https://www.continuum.io/downloads>`_
2. Install the R Essentials package into the current environment: ``conda install -c r r-essentials``

Create and share your own custom R bundle
=========================================

Building and sharing your own custom R bundles with others is like building and sharing conda packages.

For example, create a simple custom R bundle meta-package named "Custom-R-Bundle" containing several popular programs and their dependencies with the command::

  conda metapackage custom-r-bundle 0.1.0 --dependencies r-irkernel jupyter r-ggplot2 r-dplyr --summary "My custom R bundle"

Now you can easily share your new meta-package with friends and colleagues by uploading it to your channel on `Anaconda Cloud <https://anaconda.org>`_::

  conda install anaconda-client
  anaconda login
  anaconda upload path/to/custom-r-bundle-0.1.0-0.tar.bz2

Your friends and colleagues now have access to your Custom-R-Bundle from any computer with the command::

  conda install -c <your anaconda.org username> custom-r-bundle

For more information, see Christine Doig's blog post `Jupyter and conda for R <https://www.continuum.io/blog/developer/jupyter-and-conda-r>`_.

Next, let's look at :doc:`mro`.
