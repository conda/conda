# (c) Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import os
import sys
from os.path import isdir, basename, exists, abspath

import conda.config as config
import conda.plan as plan
from conda.api import get_index
from conda.cli import pscheck
from conda.cli import common
from conda.misc import touch_nonadmin
import conda.install as ci

def install_tar(prefix, tar_path, verbose=False):
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

def check_prefix(prefix):
    from conda.config import root_env_name

    name = basename(prefix)
    if name.startswith('.'):
        sys.exit("Error: environment name cannot start with '.': %s" % name)
    if name == root_env_name:
        sys.exit("Error: '%s' is a reserved environment name" % name)
    if exists(prefix):
        sys.exit("Error: prefix already exists: %s" % prefix)

def clone(src_arg, dst_prefix):
    from conda.misc import clone_env

    if os.sep in src_arg:
        src_prefix = abspath(src_arg)
        if not isdir(src_prefix):
            sys.exit('Error: could such directory: %s' % src_arg)
    else:
        src_prefix = common.find_prefix_name(src_arg)
        if src_prefix is None:
            sys.exit('Error: could not find environment: %s' % src_arg)

    print("src_prefix: %r" % src_prefix)
    print("dst_prefix: %r" % dst_prefix)
    clone_env(src_prefix, dst_prefix)

def print_activate(arg):
    print("#")
    print("# To activate this environment, use:")
    if sys.platform == 'win32':
        print("# > activate %s" % arg)
    else:
        print("# $ source activate %s" % arg)
        print("#")
        print("# To deactivate this environment, use:")
        print("# $ source deactivate")
    print("#")

def install(args, parser, command='install'):
    """
    conda install, conda update, and conda create
    """

    newenv = command == 'create'
    if newenv:
        common.ensure_name_or_prefix(args, command)
    prefix = common.get_prefix(args, search=not newenv)
    if newenv:
        check_prefix(prefix)
    config.set_pkgs_dirs(prefix)

    if command == 'update':
        if len(args.packages) == 0:
            sys.exit("""Error: no package names supplied
# If you want to update to a newer version of Anaconda, type:
#
# $ conda update --prefix %s anaconda
""" % prefix)

    if command == 'update':
        linked = set(ci.name_dist(d) for d in ci.linked(prefix))
        for name in args.packages:
            common.arg2spec(name)
            if '=' in name:
                sys.exit("Invalid package name: '%s'" % (name))
            if name not in linked:
                sys.exit("Error: package '%s' is not installed in %s" %
                         (name, prefix))

    if newenv and args.clone:
        if args.packages:
            sys.exit('Error: did not expect any arguments for --clone')
        clone(args.clone, prefix)
        touch_nonadmin(prefix)
        print_activate(args.name if args.name else prefix)
        return

    if newenv and not args.no_default_packages:
        args.packages.extend(config.create_default_packages)

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

    if not isdir(prefix) and not newenv:
        if args.mkdir:
            try:
                os.makedirs(prefix)
            except OSError:
                sys.exit("Error: could not create directory: %s" % prefix)
        else:
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
        try:
            from conda_build import config as build_config
        except ImportError:
            sys.exit("Error: you need to have 'conda-build' installed"
                     " to use the --use-local option")
        # remove the cache such that a refetch is made,
        # this is necessary because we add the local build repo URL
        fetch_index.cache = {}
        index = get_index([url_path(build_config.croot)])

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
    if command in {'install', 'update'}:
        common.check_write(command, prefix)

    if not pscheck.main(args):
        common.confirm_yn(args)

    plan.execute_actions(actions, index, verbose=not args.quiet)
    if newenv:
        touch_nonadmin(prefix)
        print_activate(args.name if args.name else prefix)
