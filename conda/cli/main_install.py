# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from argparse import RawDescriptionHelpFormatter

import utils


descr = "Install a list of packages into a specified conda environment."
example = """
examples:
    conda install -n myenv scipy

"""

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'install',
        formatter_class = RawDescriptionHelpFormatter,
        description = descr,
        help = descr,
        epilog = example,
    )
    utils.add_parser_yes(p)
    p.add_argument(
        '-f', "--force",
        action = "store",
        help = "force install (even when package already installed)",
    )
    p.add_argument(
        "--file",
        action = "store",
        help = "read package versions from FILE",
    )
    utils.add_parser_prefix(p)
    utils.add_parser_quiet(p)
    p.add_argument(
        'packages',
        metavar = 'package_version',
        action = "store",
        nargs = '*',
        help = "package versions to install into conda environment",
    )
    p.set_defaults(func=execute)


def execute(args, parser):
    import conda.plan as plan
    from conda.api import get_index

    prefix = utils.get_prefix(args)

    if args.file:
        specs = utils.specs_from_file(args.file)
    else:
        specs = utils.specs_from_args(args.packages)

    utils.check_specs(prefix, specs)

    # TODO...
    #if all(s.endswith('.tar.bz2') for s in req_strings):
    #    from conda.install import install_local_package
    #    for path in req_strings:
    #        install_local_package(path, config.pkgs_dir, prefix)
    #    return
    #if any(s.endswith('.tar.bz2') for s in req_strings):
    #    raise RuntimeError("mixing specifications and filename not supported")

    # TODO: --force
    index = get_index()
    actions = plan.install_actions(prefix, index, specs)

    if plan.nothing_to_do(actions):
        print('All requested packages already installed into '
              'environment: %s' % prefix)
        return

    print
    print "Package plan for installation in environment %s:" % prefix
    plan.display_actions(actions)

    utils.confirm(args)
    plan.execute_actions(actions, index, enable_progress=not args.quiet)
