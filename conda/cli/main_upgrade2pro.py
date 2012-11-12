
import logging

from anaconda import anaconda
from package_plan import package_plan


log = logging.getLogger(__name__)


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'upgrade2pro',
        description     = "Upgrade Anaconda install to AnacondaPro trial.",
        help            = "Upgrade Anaconda install to AnacondaPro trial.",
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
    p.set_defaults(func=execute)


def execute(args):
    conda = anaconda()

    idx = conda.index

    env = conda.default_environment
    env_reqs = env.get_requirements('pro')

    candidates = idx.lookup_from_name('anaconda')
    candidates = idx.find_matches(env_reqs, candidates)
    candidate = max(candidates)

    log.debug('anaconda version to upgrade to: %s' % candidate.canonical_name)

    plan = package_plan()

    to_install = set([candidate])
    pkgs = to_install

    # find the associated dependencies
    reqs = idx.get_deps(pkgs)
    to_remove = set()
    for req in reqs:
        if env.requirement_is_satisfied(req):
            to_remove.add(req)
    reqs = reqs - to_remove

    # find packages compatible with the full requirements and build target
    all_pkgs = idx.find_compatible_packages(reqs) | to_install
    all_pkgs = idx.find_matches(env_reqs, all_pkgs)

    # download any packages that are not available
    for pkg in all_pkgs:

        # download any currently unavailable packages
        if pkg not in env.conda.available_packages:
            plan.downloads.add(pkg)

        # see if the package is already active
        active = env.find_activated_package(pkg.name)
        if active:
            if pkg != active or pkg.name == 'anaconda':
                plan.deactivations.add(active)

        if pkg not in env.activated:
            plan.activations.add(pkg)

    print "Upgrading Anaconda installation to AnacondaPro"

    print plan

    if args.dry_run: return

    if args.confirm == "yes":
        proceed = raw_input("Proceed (y/n)? ")
        if proceed.lower() not in ['y', 'yes']: return

    plan.execute(env)
