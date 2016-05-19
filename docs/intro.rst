Intro to conda
==============

**Conda** is a package manager application that quickly installs, runs, and updates packages and their dependencies.  The **conda command** is the primary interface for managing installations of various packages. It can query and search the package index and current installation, create new environments, and install and update packages into existing conda environments. See our 
:doc:`/using/index` section for more information.

Conda is also an environment manager application. A **conda environment** is a directory that contains a specific collection of conda packages that you have installed. For example, you may have one environment with NumPy 1.7 and its dependencies, and another environment with NumPy 1.6 for legacy testing. If you change one environment, your other environments are not affected. You can easily activate or deactivate (switch between) these environments. You can also share your environment with someone by giving them a copy of your environment.yaml file.

SEE ALSO: :doc:`/using/envs`.

A **conda package** is a compressed tarball file that contains system-level libraries, Python or other modules, executable programs, or other components. Conda keeps track of the dependencies between packages and platforms. 

Conda packages are downloaded from remote channels, which are simply URLs to directories containing conda packages. The conda command searches a default set of channels, and packages are automatically downloaded and updated from  http://repo.continuum.io/pkgs/. 

SEE ALSO: :doc:`/using/pkgs`.

Users may modify what remote channels are automatically searched, for example, if they wish to maintain a private or internal channel (see Configuration for details). 

The **conda build** command creates new packages that can be optionally uploaded to a repository such as PyPi, GitHub, or Anaconda.org. 

SEE ALSO: :doc:`building/build` and :doc:`glossary`.
