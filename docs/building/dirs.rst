Directory structure
-------------------

The conda system has the following directory structure:

**ROOT_DIR**
    The directory that Anaconda (or Miniconda) was installed
    into; for example, */opt/Anaconda* or *C:\\Anaconda*

    */pkgs*
        Also referred to as *PKGS_DIR*. This directory contains exploded
        packages, ready to be linked in conda environments.
        Each package resides in a subdirectory corresponding to its
        canonical name.

    */envs*
        The system location for additional conda environments to be created.

    |   */bin*
    |   */include*
    |   */lib*
    |   */share*
    |       These subdirectories comprise the default Anaconda environment.

Other conda environments usually contain the same subdirectories as the
default environment.
