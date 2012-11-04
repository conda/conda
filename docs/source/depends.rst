-------
depends
-------

Query Anaconda package dependencies.

**usage**: conda depends [-h] [-m MAX_DEPTH] [-n] [-p PREFIX] [-r] [-v] package_name [package_name ...]

*package_name*
    package name to query on

optional arguments:
    -h, --help          show this help message and exit
    -m MAX_DEPTH, --max-depth MAX_DEPTH
                        maximum depth to search dependencies, 0 searches all
                        depths (default: 0)
    -n, --no-prefix     return reverse dependencies compatible with any
                        specified environment, overrides --prefix
    -p PREFIX, --prefix PREFIX
                        return dependencies compatible with a specified
                        environment (default: ROOT_DIR)
    -r, --reverse       generate reverse dependencies
    -v, --verbose       display build strings on reverse dependencies
