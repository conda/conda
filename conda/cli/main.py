"""conda is a tool for managing Anaconda environments and packages.

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

    create     : create a new Anaconda environment from a list of specified packages
    install    : install new packages into an existing Anaconda environment
    upgrade    : upgrade packages in a sepcified Anaconda environment

    Advanced Package Management
    ===========================

    activate   : activate available packages in a specified Anaconda environment
    deactivate : deactivate packages in a specified Anaconda environment
    download   : download and make available packages from remote repositories
    remove     : remove specified packages from the local packages repository

Additional help for each command can be accessed by using:

    conda <command> -h
"""

from difflib import get_close_matches
import re

import conda_argparse as argparse
import main_activate
import main_create
import main_deactivate
import main_depends
import main_download
import main_envs
import main_info
import main_install
import main_list
import main_locations
import main_remove
import main_search
import main_upgrade


def main():

    import logging
    from .. import __version__

    p = argparse.ArgumentParser()
    p.add_argument(
        '-v', '--version',
        action='version',
        version=' ' .join(['%(prog)s', '%s' % __version__])
    )
    p.add_argument(
        '-l', "--log-level",
        action  = "store",
        default = "warning",
        choices = ['info', 'warning', 'error', 'critical'],
        help    = argparse.SUPPRESS,
    )

    sub_parsers = p.add_subparsers(
        title   = 'informational commands',
        metavar = 'command',
        dest    = 'cmd',
    )

    main_info.configure_parser(sub_parsers)
    main_list.configure_parser(sub_parsers)
    main_depends.configure_parser(sub_parsers)
    main_search.configure_parser(sub_parsers)
    main_locations.configure_parser(sub_parsers)
    main_envs.configure_parser(sub_parsers)
    main_create.configure_parser(sub_parsers)
    main_install.configure_parser(sub_parsers)
    main_upgrade.configure_parser(sub_parsers)
    main_activate.configure_parser(sub_parsers)
    main_deactivate.configure_parser(sub_parsers)
    main_download.configure_parser(sub_parsers)
    main_remove.configure_parser(sub_parsers)

    try:
        args = p.parse_args()
    except argparse.ArgumentError as e:
        # this is incredibly lame, but argparse stupidly does not expose reasonable hooks
        # for customizing error handling
        m = re.compile(r"invalid choice: '(\w+)'").match(e.message)
        if m:
            cmd = m.group(1)
            print "conda: error: %r is not a conda command, see 'conda -h'" % cmd
            close = get_close_matches(cmd, sub_parsers.choices.keys())
            if close:
                print
                print 'Did you mean one of these?'
                print
                for s in close:
                    print '    %s' % s
                print
        else:
            print e
        raise SystemExit(1)

    log_level = getattr(logging, args.log_level.upper())
    logging.basicConfig(level=log_level)

    args.func(args, p)

if __name__ == '__main__':
    main()
