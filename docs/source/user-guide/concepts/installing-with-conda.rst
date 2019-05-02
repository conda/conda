=====================
Installing with conda
=====================

.. image:: /img/installing-with-conda.png
    :align: right

.. _installing-with-conda:


To install conda packages, in the terminal or an Anaconda Prompt, run::

  conda install [packagename]


During the install process, files are extracted into the specified
environment, defaulting to the current environment if none is specified.
Installing the files of a conda package into an
environment can be thought of as changing the directory to an
environment, and then downloading and extracting the artifact
and its dependencies---all with the single
``conda install [packagename]`` command.

Read more about :doc:`conda environments and directory structure <../concepts/environments>`.

* When you ``conda install`` a package that exists in a channel and has no dependencies, conda:

  * looks at your configured channels (in priority)

  * reaches out to the repodata associated with your channels/platform

  * parses repodata to search for the package

  * once the package is found, conda pulls it down and installs

