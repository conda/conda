# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

from argparse import RawDescriptionHelpFormatter

from conda.cli import common
from conda.from_pypi import install_from_pypi, install_with_pip


help = "Install a list of packages into a specified conda environment."
descr = help + """
The arguments may be packages specifications (e.g. bitarray=0.8),
or explicit conda packages filesnames (e.g. lxml-3.2.0-py27_0.tar.bz2) which
must exist on the local filesystem.  The two types of arguments cannot be
mixed and the latter implied the --force and --no-deps options.
"""
example = """
examples:
    conda install -n myenv scipy

"""

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'install',
        formatter_class = RawDescriptionHelpFormatter,
        description = descr,
        help = help,
        epilog = example,
    )
    common.add_parser_yes(p)
    p.add_argument(
        '-f', "--force",
        action = "store_true",
        help = "force install (even when package already installed), "
               "implies --no-deps",
    )
    p.add_argument(
        "--file",
        action = "store",
        help = "read package versions from FILE",
    )
    p.add_argument(
        "--no-deps",
        action = "store_true",
        help = "do not install dependencies",
    )
    p.add_argument(
        "--no-pip",
        action = "store_false",
        default=True,
        dest="pip",
        help = "do not use pip to install if conda fails",
    )
    p.add_argument(
        "--use-pypi",
        action = "store_true",
        default=False,
        dest="pypi",
        help = "build a package from pypi if conda install fails",
    )
    p.add_argument(
        "--use-local",
        action="store_true",
        default=False,
        dest='use_local',
        help = "use locally built packages",
    )
    common.add_parser_channels(p)
    common.add_parser_prefix(p)
    common.add_parser_quiet(p)
    p.add_argument(
        'packages',
        metavar = 'package_spec',
        action = "store",
        nargs = '*',
        help = "package versions to install into conda environment",
    )
    p.set_defaults(func=execute)


def install_tar(prefix, tar_path, verbose=False):
    import os
    import shutil
    import tarfile
    import tempfile
    from os.path import join

    from conda.misc import install_local_packages

    tmp_dir = tempfile.mkdtemp()
    t = tarfile.open(tar_path, 'r')
    t.extractall(path=tmp_dir)
    t.close()

    paths = []
    for root, dirs, files in os.walk(tmp_dir):
        for fn in files:
            if fn.endswith('.tar.bz2'):
                paths.append(join(root, fn))

    install_local_packages(prefix, paths, verbose=verbose)

    shutil.rmtree(tmp_dir)


def execute(args, parser):
    import sys
    from os.path import isdir

    import conda.config as config
    import conda.plan as plan
    from conda.api import get_index
    from conda.cli import pscheck


    prefix = common.get_prefix(args)
    config.set_pkgs_dirs(prefix)

    # handle tar file containaing conda packages
    if len(args.packages) == 1:
        tar_path = args.packages[0]
        if tar_path.endswith('.tar'):
            install_tar(prefix, tar_path, verbose=not args.quiet)
            return

    # handle explict installs of conda packages
    if args.packages and all(s.endswith('.tar.bz2') for s in args.packages):
        from conda.misc import install_local_packages
        install_local_packages(prefix, args.packages, verbose=not args.quiet)
        return

    if any(s.endswith('.tar.bz2') for s in args.packages):
        sys.exit("cannot mix specifications with conda package filenames")

    if args.force:
        args.no_deps = True

    if args.file:
        specs = common.specs_from_url(args.file)
    else:
        specs = common.specs_from_args(args.packages)

    common.check_specs(prefix, specs)

    spec_names = set(s.split()[0] for s in specs)
    if args.no_deps:
        only_names = spec_names
    else:
        only_names = None

    if not isdir(prefix):
        sys.exit("""\
Error: environment does not exist: %s
#
# Use 'conda create' to create an environment before installing packages
# into it.
#""" % prefix)

    common.ensure_override_channels_requires_channel(args)
    channel_urls = args.channel or ()
    index = get_index(channel_urls=channel_urls, prepend=not
        args.override_channels)

    if args.use_local:
        from conda.fetch import fetch_index
        from conda.utils import url_path
        from conda.builder import config as build_config
        # remove the cache such that a refetch is made,
        # this is necessary because we add the local build repo URL
        fetch_index.cache = {}
        index = get_index([url_path(build_config.croot)])

    if args.pip:
        # Remove from specs packages that are not in conda index
        #  and install them using pip
        # Return the updated specs
        specs = install_with_pip(prefix, index, specs)
        if not specs: return

    elif args.pypi:
        # Remove from specs packages that are not in conda index
        # And install them via pypi method
        # Return an updated specs
        specs = install_from_pypi(prefix, index, specs)
        if not specs: return

    actions = plan.install_actions(prefix, index, specs,
                                   force=args.force, only_names=only_names)

    if plan.nothing_to_do(actions):
        from conda.cli.main_list import list_packages

        regex = '^(%s)$' % '|'.join(spec_names)
        print('# All requested packages already installed.')
        list_packages(prefix, regex)
        return

    print()
    print("Package plan for installation in environment %s:" % prefix)
    plan.display_actions(actions, index)
    common.check_write('install', prefix)

    if not pscheck.main(args):
        common.confirm_yn(args)

    plan.execute_actions(actions, index, verbose=not args.quiet)
