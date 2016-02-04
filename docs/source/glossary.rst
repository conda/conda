========
Glossary
========

Please see also the :doc:`/using/cheatsheet`.

.condarc: 
  Conda configuration file, an optional runtime configuration YAML file which allows users to configure many aspects of conda, such as which channels it searches for packages, proxy settings, environment directories, etc. A .condarc file is not included by default, but when you use the ‘conda config’ command it is automatically created in the user’s home directory. The .condarc file can also be located in a root environment, in which case it overrides any in the home directory.  See :doc:`conda configuration </config>` documentation for more information. 

Activate/deactivate environment: 
  Conda commands used to switch or move between installed environments. Activate prepends the path of your current environment to PATH environment variable, and deactivate removes it. Even when an environment is not activated, programs in that environment can still be executed by specifying their path directly, as in ‘~/anaconda/envs/envname/bin/program_name’. When an environment is activated, you can just use ‘program_name’.

Anaconda: 
  An easy-to-install, free collection of Open Source packages, including Python and the conda package manager, with free community support. Over 150 packages are installed with Anaconda. The Anaconda repository contains those 150 and over 250 more Open Source packages that can be installed or updated after installing Anaconda with the conda command.

Channels: 
  The URLs to the repositories where conda looks for packages. Channels may point to a remote repository website, Anaconda.org repository, a private repository or a local repository that you have created. The conda channel command starts with a default set of channels to search, but users may override this, for example, to maintain a private or internal channel. These default channels are referred to in conda commands and in the .condarc by the channel name ‘defaults’.

Conda: 
  The conda package manager and environment manager program that installs and updates packages and their dependencies, and lets you easily switch between environments on your local computer.  

Conda environment:  
  A directory that contains a specific collection of conda packages. For example, you can have one environment for Python 2 and Python 2 packages, and another environment with Python 3 and Python 3 packages.  Environments are normally stored in the envs directory of your conda directory, but they may just as easily be stored anywhere. 

Conda package: 
  A tarball (compressed file) containing system-level libraries, Python modules, executable programs, or other components. For a package to be a “conda package” it must follow the conda package specification.

Metapackage: 
  A conda package that only lists dependencies, and does not include any functional programs of libraries itself. The metapackage may contain links to software files that will be automatically downloaded when executed. An example of a metapackage is ‘anaconda’, which collects together all the packages in the Anaconda installer, thus, ‘conda create -n envname anaconda’ will create an environment that exactly matches what would be created from the Anaconda installer. 

Miniconda: 
  A minimal installer for conda. Like Anaconda, Miniconda is a software package that includes the conda package manager and Python and its dependencies, but Miniconda does not include any other packages. Once conda is installed by installing either Anaconda or miniconda, other software packages may be installed directly from the command line with ‘conda install’. See also Anaconda and conda.

Noarch package:
  A conda package that contains nothing specific to any system architecture, so it may be installed from any system. When conda does a search for packages on any system in a channel, conda always checks both the system-specific subdirectory, for example, "linux-64" *and* the ``noarch`` directory. 

Repository: 
  A storage location from which software packages may be retrieved and installed on a computer.  A repository needs to be indexed with ‘conda index’ (to generate the repodata.json file) to be usable by conda. 
