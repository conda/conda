
.. _build:

=================
Building packages
=================

Building a conda package requires 
:doc:`conda build <install-conda-build>` and involves 
creating a conda :doc:`recipe <recipe>`. Use the ``conda-build`` 
command to build the conda package from the conda recipe.

You can build conda packages from a variety of source code 
projects, most notably Python. For help packing a Python project, 
see the `Setuptools 
documentation <https://setuptools.readthedocs.io/en/latest/>`_.

TIP: If you are new to building packages with conda, 
go through the :doc:`Tutorials <../../tutorials/index>`.

OPTIONAL: If you are planning to upload your packages to 
Anaconda.org, you will need an 
`Anaconda.org <http://anaconda.org>`_ account and client.

.. toctree::
   :maxdepth: 1

   install-conda-build.rst
   package-spec.rst
   package-naming-conv.rst
   recipe.rst
   define-metadata.rst
   features.rst
   environment-variables.rst
   make-relocatable.rst
   add-scripts.rst
   variants.rst
   use-shared-libraries.rst
   sign-packages.rst
   add-win-start-menu-items.rst
   sample-recipes.rst
   build-without-recipe.rst
