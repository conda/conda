----------
deactivate
----------

Deactivate packages in an Anaconda environment.

**usage**: conda deactivate [-h] [--confirm {yes,no}] [--dry-run] [-p PREFIX] canonical_name [canonical_name ...]

*canonical_name*
    canonical name of package to deactivate from Anaconda environment

optional arguments:
    -h, --help          show this help message and exit
    --confirm           ask for confirmation before deactivating packages
                        (default: yes)
    --dry-run           display packages to be deactivated, without actually
                        executing (default: False)
    -p PREFIX, --prefix PREFIX
                        deactivate from a specified environment (default: ROOT_DIR)
