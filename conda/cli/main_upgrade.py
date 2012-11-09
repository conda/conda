
from os.path import abspath, expanduser, join

from anaconda import anaconda
from config import ROOT_DIR
from package_plan import create_upgrade_plan


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'upgrade',
        description     = "Upgrade Anaconda packges.",
        help            = "Upgrade Anaconda packges.",
    )
    p.add_argument(
        "--confirm",
        action  = "store",
        default = "yes",
        choices = ["yes", "no"],
        help    = "ask for confirmation before upgrading packages (default: yes)",
    )
    p.add_argument(
        "--dry-run",
        action  = "store_true",
        default = False,
        help    = "display packages to be modified, without actually exectuting",
    )
    npgroup = p.add_mutually_exclusive_group()
    npgroup.add_argument(
        '-n', "--name",
        action  = "store",
        help    = "name of new directory (in %s/envs) to upgrade packages in" % ROOT_DIR,
    )
    npgroup.add_argument(
        '-p', "--prefix",
        action  = "store",
        default = ROOT_DIR,
        help    = "full path to Anaconda environment to upgrade packages in (default: %s)" % ROOT_DIR,
    )
    p.add_argument(
        'pkg_names',
        metavar = 'package_name',
        action  = "store",
        nargs   = '*',
        help    = "names of packages to upgrade (default: all packages)",
    )
    p.set_defaults(func=execute)


def execute(args):
    conda = anaconda()

    if args.name:
        prefix = join(ROOT_DIR, 'envs', args.name)
    else:
        prefix = abspath(expanduser(args.prefix))

    env = conda.lookup_environment(prefix)

    if len(args.pkg_names) == 0:
        pkgs = env.activated
    else:
        pkgs = set()
        for pkg_name in args.pkg_names:
            pkg = env.find_activated_package(pkg_name)
            if not pkg:
                if pkg_name in conda.index.package_names:
                    raise RuntimeError("package '%s' is not installed, cannot upgrade (see conda install -h)" % pkg_name)
                else:
                    raise RuntimeError("unknown package '%s', cannot upgrade" % pkg_name)
            pkgs.add(pkg)

    plan = create_upgrade_plan(env, pkgs)

    if plan.empty():
        print 'All packages already at latest version'
        return

    print "Upgrading Anaconda environment at %s" % args.prefix

    print plan

    if args.dry_run: return

    if args.confirm == "yes":
        proceed = raw_input("Proceed (y/n)? ")
        if proceed.lower() not in ['y', 'yes']: return

    plan.execute(env)

