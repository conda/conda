# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

import logging
import sys

from conda.anaconda import Anaconda
from conda.config import CIO_PRO_CHANNEL
from conda.package_plan import PackagePlan
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
    if 'Anaconda ' in sys.version:
        raise RuntimeError('Already upgraded to full Anaconda')

    conda = Anaconda(first_channel=CIO_PRO_CHANNEL)

    idx = conda.index

    env = conda.root_environment

    candidates = idx.lookup_from_name('anaconda')
    candidates = [candidate for candidate in candidates if CIO_PRO_CHANNEL in candidate.channel]
    candidates = idx.find_matches(env.requirements, candidates)
    if len(candidates) == 0:
        raise RuntimeError("No Anaconda upgrade packages could be found (possibly missing internet connection?)")
    pkg = max(candidates)

    log.debug('anaconda version to upgrade to: %s' % pkg.canonical_name)

    plan = PackagePlan()

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

    plan.execute(env, channels=conda.channel_urls)
