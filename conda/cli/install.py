# (c) Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import os
import sys
import shutil
import tarfile
import tempfile
from os.path import isdir, join, basename, exists, abspath

import conda.config as config
import conda.plan as plan
from conda.api import get_index
from conda.cli import pscheck
from conda.cli import common
from conda.misc import touch_nonadmin
from conda.resolve import Resolve, MatchSpec
import conda.install as ci


def install_tar(prefix, tar_path, verbose=False):
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


def get_revision(arg):
    try:
        return int(arg)
    except ValueError:
        sys.exit("Error: expected revision number, not: '%s'" % arg)


def install(args, parser, command='install'):
    """
    conda install, conda update, and conda create
    """
    newenv = bool(command == 'create')
    if newenv:
        common.ensure_name_or_prefix(args, command)
    prefix = common.get_prefix(args, search=not newenv)
    if newenv:
        check_prefix(prefix)

    if command == 'update':
        if args.all:
            if args.packages:
                sys.exit("""Error: --all cannot be used with packages""")
        else:
            if len(args.packages) == 0:
                sys.exit("""Error: no package names supplied
# If you want to update to a newer version of Anaconda, type:
#
# $ conda update --prefix %s anaconda
""" % prefix)

    if command == 'update':
        linked = ci.linked(prefix)
        for name in args.packages:
            common.arg2spec(name)
            if '=' in name:
                sys.exit("Invalid package name: '%s'" % (name))
            if name not in set(ci.name_dist(d) for d in linked):
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
        default_packages = config.create_default_packages[:]
        # Override defaults if they are specified at the command line
        for default_pkg in config.create_default_packages:
            if any(pkg.split('=')[0] == default_pkg for pkg in args.packages):
                default_packages.remove(default_pkg)
        args.packages.extend(default_packages)

    common.ensure_override_channels_requires_channel(args)
    channel_urls = args.channel or ()

    if args.file:
        specs = common.specs_from_url(args.file)
    elif getattr(args, 'all', False):
        specs = []
        linked = ci.linked(prefix)
        for pkg in linked:
            name, ver, build = pkg.rsplit('-', 2)
            if name == 'python' and ver.startswith('2'):
                # Oh Python 2...
                specs.append('%s >=%s,<3' % (name, ver))
            else:
                specs.append('%s >=%s' % (name, ver))
    else:
        specs = common.specs_from_args(args.packages)

    if command == 'install' and args.revision:
        get_revision(args.revision)
    else:
        common.check_specs(prefix, specs)

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
        index = get_index([url_path(build_config.croot)],
                          use_cache=args.use_index_cache,
                          unknown=args.unknown)
    else:
        index = get_index(channel_urls=channel_urls, prepend=not
                          args.override_channels,
                          use_cache=args.use_index_cache,
                          unknown=args.unknown)

    # Don't update packages that are already up-to-date
    if command == 'update' and not args.all:
        r = Resolve(index)
        orig_packages = args.packages[:]
        for name in orig_packages:
            vers_inst = [dist.rsplit('-', 2)[1] for dist in linked
                if dist.rsplit('-', 2)[0] == name]
            build_inst = [dist.rsplit('-', 2)[2].rsplit('.tar.bz2', 1)[0]
                          for dist in linked
                          if dist.rsplit('-', 2)[0] == name]
            assert len(vers_inst) == 1, name
            assert len(build_inst) == 1, name
            pkgs = sorted(r.get_pkgs(MatchSpec(name)))
            if not pkgs:
                # Shouldn't happen?
                continue
            latest = pkgs[-1]
            if latest.version == vers_inst[0] and latest.build == build_inst[0]:
                args.packages.remove(name)
        if not args.packages:
            from conda.cli.main_list import list_packages

            regex = '^(%s)$' % '|'.join(orig_packages)
            print('# All requested packages already installed.')
            list_packages(prefix, regex)
            return

    # handle tar file containing conda packages
    if len(args.packages) == 1:
        tar_path = args.packages[0]
        if tar_path.endswith('.tar'):
            install_tar(prefix, tar_path, verbose=not args.quiet)
            return

    # handle explicit installs of conda packages
    if args.packages and all(s.endswith('.tar.bz2') for s in args.packages):
        from conda.misc import install_local_packages
        install_local_packages(prefix, args.packages, verbose=not args.quiet)
        return

    if any(s.endswith('.tar.bz2') for s in args.packages):
        sys.exit("cannot mix specifications with conda package filenames")

    if args.force:
        args.no_deps = True

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

    if command == 'install' and args.revision:
        actions = plan.revert_actions(prefix, get_revision(args.revision))
    else:
        actions = plan.install_actions(prefix, index, specs, force=args.force,
                                       only_names=only_names, pinned=args.pinned, minimal_hint=args.alt_hint)

    if plan.nothing_to_do(actions):
        from conda.cli.main_list import list_packages

        regex = '^(%s)$' % '|'.join(spec_names)
        print('\n# All requested packages already installed.')
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


def check_install(packages, platform=None, channel_urls=(), prepend=True, minimal_hint=False):
    try:
        prefix = tempfile.mkdtemp('conda')
        specs = common.specs_from_args(packages)
        index = get_index(channel_urls=channel_urls, prepend=prepend,
                          platform=platform)
        plan.install_actions(prefix, index, specs, pinned=False, minimal_hint=minimal_hint)
    finally:
        ci.rm_rf(prefix)
