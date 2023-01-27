-----------------------------------------
RPM and Debian Repositories for Miniconda
-----------------------------------------
Conda, the package manager from Anaconda, is available as either a RedHat RPM or as a Debian package. The packages are the equivalent to the Miniconda installer which only contains conda and its dependencies. You can use yum or apt to install, uninstall and manage conda on your system. To install conda, follow the instructions for your Linux distribution.

To install the RPM on RedHat, CentOS, Fedora distributions, and other RPM-based distributions such as openSUSE, download the GPG key and add a repository configuration file for conda.

.. code-block:: none

   # Import our GPG public key
   rpm --import https://repo.anaconda.com/pkgs/misc/gpgkeys/anaconda.asc

   # Add the Anaconda repository
   cat <<EOF > /etc/yum.repos.d/conda.repo
   [conda]
   name=Conda
   baseurl=https://repo.anaconda.com/pkgs/misc/rpmrepo/conda
   enabled=1
   gpgcheck=1
   gpgkey=https://repo.anaconda.com/pkgs/misc/gpgkeys/anaconda.asc
   EOF

Conda is ready to install on your RPM-based distribution.

.. code-block:: none

   # Install it!
   yum install conda
   Loaded plugins: fastestmirror, ovl
   Setting up Install Process
   Loading mirror speeds from cached hostfile
    * base: repo1.dal.innoscale.net
    * extras: mirrordenver.fdcservers.net
    * updates: mirror.tzulo.com
   Resolving Dependencies
   --> Running transaction check
   ---> Package conda.x86_64 0:4.5.11-0 will be installed
   --> Finished Dependency Resolution

   Dependencies Resolved


 ===============================================================================
   Package         Arch        Version             Repository            Size

 ===============================================================================
   Installing:
   conda           x86_64      4.5.11-0            conda                 73 M

   Transaction Summary

 ===============================================================================
   Install   	1 Package(s)

   Total download size: 73 M
   Installed size: 210 M
   Is this ok [y/N]:

To install on Debian-based Linux distributions such as Ubuntu, download the public GPG key and add the conda repository to the sources list.

.. code-block:: none

   # Install our public GPG key to trusted store
   curl https://repo.anaconda.com/pkgs/misc/gpgkeys/anaconda.asc | gpg --dearmor > conda.gpg
   install -o root -g root -m 644 conda.gpg /usr/share/keyrings/conda-archive-keyring.gpg

   # Check whether fingerprint is correct (will output an error message otherwise)
   gpg --keyring /usr/share/keyrings/conda-archive-keyring.gpg --no-default-keyring --fingerprint 34161F5BF5EB1D4BFBBB8F0A8AEB4F8B29D82806

   # Add our Debian repo
   echo "deb [arch=amd64 signed-by=/usr/share/keyrings/conda-archive-keyring.gpg] https://repo.anaconda.com/pkgs/misc/debrepo/conda stable main" > /etc/apt/sources.list.d/conda.list

   **NB:** If you receive a Permission denied error when trying to run the above command (because `/etc/apt/sources.list.d/conda.list` is write protected), try using the following command instead:
   echo "deb [arch=amd64 signed-by=/usr/share/keyrings/conda-archive-keyring.gpg] https://repo.anaconda.com/pkgs/misc/debrepo/conda stable main" | sudo tee -a /etc/apt/sources.list.d/conda.list

Conda is ready to install on your Debian-based distribution.

.. code-block:: none

   # Install it!
   apt update
   apt install conda
   Reading package lists... Done
   Building dependency tree
   Reading state information... Done
   The following NEW packages will be installed:
   conda
   0 upgraded, 1 newly installed, 0 to remove and 3 not upgraded.
   Need to get 76.3 MB of archives.
   After this operation, 221 MB of additional disk space will be used.
   Get:1 https://repo.anaconda.com/pkgs/misc/debrepo/conda stable/main amd64
   conda amd64 4.5.11-0 [76.3 MB]
   Fetched 76.3 MB in 10s (7733 kB/s)
   debconf: delaying package configuration, since apt-utils is not installed
   Selecting previously unselected package conda.
   (Reading database ... 4799 files and directories currently installed.)
   Preparing to unpack .../conda_4.5.11-0_amd64.deb ...
   Unpacking conda (4.5.11-0) ...
   Setting up conda (4.5.11-0) …

Check to see if the installation is successful by typing:

.. code-block:: none

   source /opt/conda/etc/profile.d/conda.sh
   conda -V
   conda 4.5.11


Installing conda packages with the system package manager makes it very easy
to distribute conda across a cluster of machines running Linux without having
to worry about any non-privileged user modifying the installation.
Any non-privileged user simply needs to run ``source /opt/conda/etc/profile.d/conda.sh`` to use conda.

Administrators can also distribute a .condarc file at /opt/conda/.condarc so that a
predefined configuration for channels, package cache directory, and environment locations
is pre-seeded to all users in a large organization. A sample configuration could look like:

.. code-block:: none

   channels:
   defaults
   pkg_dirs:
   /shared/conda/pkgs
   $HOME/.conda/pkgs
   envs_dirs:
   /shared/conda/envs
   $HOME/.conda/envs

These RPM and Debian packages provide another way to set up conda inside a Docker container.

It is recommended to use this installation in a read-only manner and upgrade conda using the respective package manager only.

If you’re new to conda, check out the documentation at https://conda.io/docs/
