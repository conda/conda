:orphan:

-------
upgrade
-------

Upgrade Anaconda packges to their latest version.

usage: ``conda upgrade [-h] [--confirm {yes,no}] [--dry-run] [-p PREFIX] [package_name [package_name ...]]``

*package_name*
    names of packages to upgrade (defaults to all if not specified)

optional arguments:
    -h, --help      show this help message and exit
    --confirm       ask for confirmation before upgrading packages (default: yes)
    --dry-run       display packages to be modified, without actually exectuting
    -p PREFIX, --prefix PREFIX
                    upgrade packages in the specified Anaconda environment (default: ROOT_DIR)