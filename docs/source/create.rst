:orphan:

------
create
------

Create an Anaconda environment at a specified prefix from a list of package versions.

**usage**: ``conda create [-h] [--confirm {yes,no}] [--dry-run] [-f FILE | -p [package_spec [package_spec ...]]] [--progress-bar {yes,no}] [--use-defaults {yes,no}] prefix``

*prefix*
    new directory to create Anaconda environment in

optional arguments:
    -h, --help          show this help message and exit
    --confirm           ask for confirmation before creating Anaconda environment (default: yes)
    --dry-run           display packages to be modified, without actually executing
    -f FILE, --file FILE    filename to read package versions from (default: None)
    -p, --packages
                        packages to install into new Anaconda environment
    --progress-bar      display progress bar for package downloads (default: yes)
    --use-defaults      select default versions for unspecified requirements
                        when possible (default: yes)