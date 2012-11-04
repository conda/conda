------
remove
------

Remove packages from local availability.

.. Note:: This command removes packages from PKGS_DIR, but this action will not affect any existing Anaconda environments.

**usage**: conda remove [-h] [--confirm {yes,no}] [-d] canonical_name [canonical_name ...]

*canonical_name*
    canonical name of package to remove from local availability


optional arguments:
    -h, --help      show this help message and exit
    --confirm       ask for confirmation before removing packages (default: yes)
    -d, --dry-run   display packages to be removed, without actually executing