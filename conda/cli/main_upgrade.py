# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

import logging

from conda.anaconda import anaconda
from conda.package_plan import package_plan
from utils import add_parser_yes, confirm


log = logging.getLogger(__name__)


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'upgrade',
        description     = "Upgrade Anaconda CE install to full Anaconda trial.",
        help            = "Upgrade Anaconda CE install to full Anaconda trial.",
    )
    add_parser_yes(p)
    p.set_defaults(func=execute)


def execute(args):
    conda = anaconda()

    if conda.target == 'pro':
        print "Full Anaconda already activated!"
        return

    idx = conda.index

    env = conda.root_environment
    env_reqs = env.get_requirements('pro')

    candidates = idx.lookup_from_name('anaconda')
    candidates = idx.find_matches(env_reqs, candidates)
    if len(candidates) == 0:
        raise RunTimeError("No Anaconda upgrade packages could be found (possibly missing internet connection?)")
    pkg = max(candidates)

    log.debug('anaconda version to upgrade to: %s' % pkg.canonical_name)

    plan = package_plan()

    all_pkgs = set([pkg])
    for spec in pkg.requires:
        canonical_name = "%s-%s-%s" % (spec.name, spec.version.vstring, spec.build)
        all_pkgs.add(conda.index.lookup_from_canonical_name(canonical_name))

    # download any packages that are not available
    for pkg in all_pkgs:

        # download any currently unavailable packages
        if pkg not in env.conda.available_packages:
            plan.downloads.add(pkg)

        # see if the package is already active
        active = env.find_activated_package(pkg.name)
        # need to compare canonical names since ce/pro packages might compare equal
        if active and pkg.canonical_name != active.canonical_name:
            plan.deactivations.add(active)

        if pkg not in env.activated:
            plan.activations.add(pkg)

    print "Upgrading Anaconda CE installation to full Anaconda"

    print plan

    confirm(args)

    plan.execute(env)
