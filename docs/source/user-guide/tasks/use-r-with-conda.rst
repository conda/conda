==================
Using R with conda
==================

With a single conda command you can easily install the R 
programming language and over 80 of the most used R packages for 
data science. Conda helps you keep your packages and dependencies 
up to date. You can also easily create and share your own custom 
R packages.

R Essentials works very much like Anaconda:

* You can install all of the most popular packages with all of 
  their dependencies with a single command::

    conda install -c r r-essentials

* You can update all of the packages and their dependencies with 
  a single command::

    conda update -c r r-essentials

* If a new version of a package is available in the R channel, 
  you can update that package in R Essentials with the following 
  command::
 
    conda update r-XXXX

  NOTE: Replace ``XXXX`` with the version number.


Installing R Essentials
=======================

#. `Download <https://www.continuum.io/downloads>`_ and 
   `install <https://docs.continuum.io/anaconda/install/>`_ 
   Anaconda.

#. Install the R Essentials package into the current environment: 

   .. code::

      conda install -c r r-essentials


Creating and sharing your own custom R bundle
==============================================

Creating and sharing your own custom R bundles with others is 
similar to creating and sharing conda packages.

EXAMPLE: To create a simple custom R bundle metapackage named 
"Custom-R-Bundle" that contains several popular programs and 
their dependencies, run::

   conda metapackage custom-r-bundle 0.1.0 --dependencies r-irkernel jupyter r-ggplot2 r-dplyr --summary "My custom R bundle"

[@cio-docs: Line is over the length limit.]

Now you can easily share your new metapackage with friends and 
colleagues by uploading it to your channel on `Anaconda Cloud 
<https://anaconda.org>`_::

  conda install anaconda-client
  anaconda login
  anaconda upload path/to/custom-r-bundle-0.1.0-0.tar.bz2

Your friends and colleagues can now access your custom R bundle 
from any computer by running::

  conda install -c <your anaconda.org username> custom-r-bundle

For more information, see `Jupyter and conda for R language 
<https://www.continuum.io/blog/developer/jupyter-and-conda-r>`_.
