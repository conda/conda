========
Glossary
========

Please see also the :doc:`/using/cheatsheet`.

.condarc: 
  Conda Runtime Configuration file, an optional YAML file which allows users to configure many aspects of conda, such as which channels it searches for packages, proxy settings, environment directories, etc. A .condarc file is not included by default, but when you use the ‘conda config’ command it is automatically created in the user’s home directory. The .condarc file can also be located in a root environment, in which case it overrides any in the home directory.  See :doc:`conda configuration </config>` documentation for more information. 

Activate/deactivate environment: 
  Conda commands used to switch or move between installed environments. Activate prepends the path of your current environment to PATH environment variable so you do not need to type it each time, and deactivate removes it. Even when an environment is not activated, programs in that environment can still be executed by specifying their path directly, as in ‘~/anaconda/envs/envname/bin/program_name’. When an environment is activated, you can just use ‘program_name’.

Anaconda: 
  A downloadable free, open source, high performance, optimized Python and R distribution with 100+ packages plus access to easily installing an additional 620+ popular open source packages for data science including advanced and scientific analytics. Anaconda includes conda, an open source package, dependency and environment manager. Thousands more open source packages can be installed with the conda command. Available for Windows, OS X and Linux, all versions are supported by the community.

Anaconda Cloud:
  A web-based repository hosting service in the cloud. Packages created locally can be published to the cloud to be shared with others. Free accounts on Anaconda Cloud can publish packages to be shared publicly. Paid subscriptions to Anaconda Cloud can designate packages as private to be shared with authorized users.

Anaconda Navigator:
  A desktop graphical user interface (GUI) included in all versions of Anaconda that allows you to easily manage conda packages, environments, channels and notebooks without the need to use the command line interface (CLI).

Channels: 
  The locations of the repositories where conda looks for packages. Channels may point to an Anaconda Cloud repository, a private location on a remote or local repository that you or your organization created. The conda channel command has a default set of channels to search beginning with https://repo.continuum.io/pkgs/ which users may override, for example, to maintain a private or internal channel. These default channels are referred to in conda commands and in the .condarc file by the channel name ‘defaults’.

Conda: 
  The package and environment manager program bundled with Anaconda that installs and updates conda packages and their dependencies. Also lets you easily switch between conda environments on your local computer.

Conda environment:  
  A folder or directory that contains a specific collection of conda packages and their dependencies, so they can be maintained and run separately without interference from each other. For example, you may use one conda environment for only Python 2 and Python 2 packages, maintain another conda environment with only Python 3 and Python 3 packages, and another for R language packages. Environments can be created via the command line or via an environment specification file with the name your-environment-name.yml, or from the graphical user interface of Anaconda Navigator.

Conda package: 
  A compressed file that contains everything that a software program needs in order to be installed and run (including system-level libraries, Python or R language modules, executable programs, and/or other components) so you do not have to manually find and install each dependency separately. Managed with conda.

Conda repository:
  A cloud-based repository that contains 720+ open source certified packages that are easily installed locally via the “conda install” command. May be accessed by anyone from a terminal or command prompt using conda commands, from the Anaconda Navigator GUI, or viewed directly at https://repo.continuum.io/pkgs/

Metapackage: 
  A conda package that only lists dependencies, and does not include any functional programs of libraries itself. The metapackage may contain links to software files that will be automatically downloaded when executed. An example of a metapackage is ‘anaconda’, which collects together all the packages in the Anaconda installer, thus, ‘conda create -n envname anaconda’ will create an environment that exactly matches what would be created from the Anaconda installer. 

Miniconda: 
  A minimal installer for conda. Like Anaconda, Miniconda is a free software package that includes the Anaconda distribution of Python and the conda package and environment manager and the packages they depend on, but Miniconda does not include any other packages. After Miniconda is installed, additional conda packages may be installed directly from the command line with 'conda install'. See also Anaconda and conda.

Noarch package:
  A conda package that contains nothing specific to any system architecture, so it may be installed from any system. When conda does a search for packages on any system in a channel, conda always checks both the system-specific subdirectory, for example, "linux-64" *and* the ``noarch`` directory. 

Repository: 
  Any storage location from which software software assets may be retrieved and installed on a local computer. See also Anaconda Cloud and conda repository.
