:orphan:

--------
activate
--------

Activate locally available packages in the specified Anaconda enviropnment.

**usage**: ``conda activate [-h] [--confirm {yes,no}] [--dry-run] [-p PREFIX] canonical_name [canonical_name ...]``

*canonical_name*
    canonical name of package to activate into Anaconda environment

optional arguments:
    -h, --help      show this help message and exit
    --confirm       ask for confirmation before activating packages in Anaconda environment (default: yes)
    --dry-run       display packages to be activated, without actually executing
    -p PREFIX, --prefix PREFIX
                    Anaconda environment to activate packages in (default: ROOT_DIR)