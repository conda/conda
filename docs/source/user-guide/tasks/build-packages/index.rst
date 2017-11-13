.. _build:

=================
Building packages
=================

Building a conda package requires
:doc:`installing conda build <install-conda-build>` and
creating a conda :doc:`recipe <recipe>`. Use the ``conda build``
command to build the conda package from the conda recipe.

You can build conda packages from a variety of source code
projects, most notably Python. For help packing a Python project,
see the `Setuptools
documentation <https://setuptools.readthedocs.io/en/latest/>`_.

TIP: If you are new to building packages with conda,
go through the :doc:`Tutorials <../../tutorials/index>`.

OPTIONAL: If you are planning to upload your packages to
Anaconda Cloud, you will need an
`Anaconda Cloud <http://anaconda.org>`_ account and client.

.. toctree::
   :maxdepth: 1

   install-conda-build
   package-spec
   package-naming-conv
   recipe
   define-metadata
   build-scripts
   features
   environment-variables
   make-relocatable
   link-scripts
   variants
   use-shared-libraries
   compiler-tools
   add-win-start-menu-items
   sample-recipes
   build-without-recipe
   wheel-files
