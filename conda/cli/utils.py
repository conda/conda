from datetime import datetime
from os.path import abspath, expanduser, join
import sys

from conda.config import ENVS_DIR, DEFAULT_ENV_PREFIX


def add_parser_prefix(p):
    npgroup = p.add_mutually_exclusive_group()
    npgroup.add_argument(
        '-n', "--name",
        action = "store",
        help = "name of environment (directory in %s)" % ENVS_DIR,
    )
    npgroup.add_argument(
        '-p', "--prefix",
        action = "store",
        help = "full path to environment prefix (default: %s)" %
                            DEFAULT_ENV_PREFIX,
    )


def get_prefix(args):
    if args.name:
        return join(ENVS_DIR, args.name)

    if args.prefix:
        return abspath(expanduser(args.prefix))

    return DEFAULT_ENV_PREFIX


def add_parser_yes(p):
    p.add_argument(
        "--yes",
        action = "store_true",
        default = False,
        help = "do not ask for confirmation",
    )
    p.add_argument(
        "--dry-run",
        action = "store_true",
        default = False,
        help = "only display what would have been done",
    )


def confirm(args):
    if args.dry_run:
        sys.exit(0)
    if args.yes:
        return
    # raw_input has a bug and prints to stderr, not desirable
    print "Proceed (y/n)? ",
    proceed = sys.stdin.readline()
    if proceed.strip().lower() in ('y', 'yes'):
        return
    sys.exit(0)


def add_parser_quiet(p):
    p.add_argument(
        '-q', "--quiet",
        action = "store_true",
        default = False,
        help = "do not display progress bar",
    )


def license_check_warn():
    if 'Anaconda ' in sys.version:
        exp_date = None
        try:
            import _license
            exp_date = _license.get_end_date()
        except:
            pass
        if not exp_date or datetime.today() > datetime.strptime(exp_date,
                                                                '%Y-%m-%d'):
            print("""
    Anaconda license is missing or expired. Contact sales@contium.io or visit
    http://continuum.io/anaconda.html for access to paid Anaconda channels.
            """)
