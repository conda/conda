"""conda [options] <command> [<args>]

conda is a tool for managing Anaconda environments and packages.

conda provides the following commands:

    Information
    ===========

    info       : display information about the current Anaconda install
    list       : list packages activated in a specified Anaconda environment
    depends    : find package dependencies
    search     : print information about a specificed package
    locations  : display the locations conda will search for known Anaconda environments
    envs       : list all known Anaconda environments

    Basic Package Management
    ========================

    create     : create a new Anaconda environments from a list of specified packages
    install    : install new packages into an existing Anaconda environment
    upgrade    : upgrade packages in a sepcified Anaconda environment

    Advanced Package Management
    ===========================

    activate   : activate available packages in a specified Anaconda environment
    deactivate : deactivate packages in a specified Anaconda environment
    download   : download and make available packages from remote repositories
    remove     : remove specified packages from the local packages repository

Additional help for each command can be accessed by using:

    conda help <command>
"""

import sys
from optparse import OptionParser, SUPPRESS_HELP
from difflib import get_close_matches

from anaconda import anaconda
from main_activate import main_activate
from main_create import main_create
from main_deactivate import main_deactivate
from main_depends import main_depends
from main_download import main_download
from main_envs import main_envs
from main_info import main_info
from main_install import main_install
from main_list import main_list
from main_locations import main_locations
from main_remove import main_remove
from main_search import main_search
from main_upgrade import main_upgrade


def main():

    import logging
    from .. import __version__

    p = OptionParser(
        usage       = __doc__,
        description = "Manage Anaconda packages and their dependencies.",
        version     = "%prog " + "%s" % __version__,
    )
    p.add_option(
        '-l', "--log-level",
        action  = "store",
        default = "warning",
        help    = SUPPRESS_HELP,
    )
    p.disable_interspersed_args()

    opts, args = p.parse_args(sys.argv[1:])

    if len(args) == 0:
        p.error('too few arguments')

    log_level = getattr(logging, opts.log_level.upper(), None)
    if not isinstance(log_level, int):
        raise ValueError('Invalid log level: %s' % log_level)
    logging.basicConfig(level=log_level)

    cmd, args = args[0], args[1:]

    help = False
    if cmd == 'help':
        if len(args) == 0:
            p.print_help()
            return
        help=True
        cmd, args = args[0], args[1:]

    commands = {
        'activate'  : main_activate,
        'create'    : main_create,
        'deactivate': main_deactivate,
        'depends'   : main_depends,
        'download'  : main_download,
        'info'      : main_info,
        'install'   : main_install,
        'envs'      : main_envs,
        'list'      : main_list,
        'locations' : main_locations,
        'remove'    : main_remove,
        'search'    : main_search,
        'upgrade'   : main_upgrade,
    }

    if cmd in commands:
        conda = anaconda()
        commands[cmd](args, conda, display_help=help)
    else:
        print "conda: %r is not a conda command, see 'conda -h'" % cmd
        close = get_close_matches(cmd, commands.keys())
        if close:
            print
            print 'Did you mean one of these?'
            print
            for s in close:
                print '    %s' % s


if __name__ == '__main__':
    main()
