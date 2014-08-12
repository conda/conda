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
from difflib import get_close_matches

import conda.config as config
import conda.plan as plan
from conda.api import get_index
from conda.cli import pscheck
from conda.cli import common
from conda.misc import touch_nonadmin
from conda.resolve import NoPackagesFound, Resolve, MatchSpec
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


def check_prefix(prefix, json=False):
    from conda.config import root_env_name

    name = basename(prefix)
    error = None
    if name.startswith('.'):
        error = "environment name cannot start with '.': %s" % name
    if name == root_env_name:
        error = "'%s' is a reserved environment name" % name
    if exists(prefix):
        error = "prefix already exists: %s" % prefix

    if error:
        common.error_and_exit(error, json=json, error_type="ValueError")


def clone(src_arg, dst_prefix, json=False, quiet=False):
    from conda.misc import clone_env

    if os.sep in src_arg:
        src_prefix = abspath(src_arg)
        if not isdir(src_prefix):
            common.error_and_exit('no such directory: %s' % src_arg,
                                  json=json,
                                  error_type="NoEnvironmentFound")
    else:
        src_prefix = common.find_prefix_name(src_arg)
        if src_prefix is None:
            common.error_and_exit('could not find environment: %s' % src_arg,
                                  json=json,
                                  error_type="NoEnvironmentFound")

    if not json:
        print("src_prefix: %r" % src_prefix)
        print("dst_prefix: %r" % dst_prefix)

    with common.json_progress_bars(json=json and not quiet):
        actions, untracked_files = clone_env(src_prefix, dst_prefix,
                                             verbose=not json,
                                             quiet=quiet)

    if json:
        common.stdout_json_success(
            actions=actions,
            untracked_files=list(untracked_files),
            src_prefix=src_prefix,
            dst_prefix=dst_prefix
        )


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


def get_revision(arg, json=False):
    try:
        return int(arg)
    except ValueError:
        common.error_and_exit("expected revision number, not: '%s'" % arg,
                              json=json,
                              error_type="ValueError")


def install(args, parser, command='install'):
    """
    conda install, conda update, and conda create
    """
    newenv = bool(command == 'create')
    if newenv:
        common.ensure_name_or_prefix(args, command)
    prefix = common.get_prefix(args, search=not newenv)
    if newenv:
        check_prefix(prefix, json=args.json)

    if command == 'update':
        if args.all:
            if args.packages:
                common.error_and_exit("""--all cannot be used with packages""",
                                      json=args.json,
                                      error_type="ValueError")
        else:
            if len(args.packages) == 0:
                common.error_and_exit("""no package names supplied
# If you want to update to a newer version of Anaconda, type:
#
# $ conda update --prefix %s anaconda
""" % prefix,
                                      json=args.json,
                                      error_type="ValueError")

    if command == 'update':
        linked = ci.linked(prefix)
        for name in args.packages:
            common.arg2spec(name, json=args.json)
            if '=' in name:
                common.error_and_exit("Invalid package name: '%s'" % (name),
                                      json=args.json,
                                      error_type="ValueError")
            if name not in set(ci.name_dist(d) for d in linked):
                common.error_and_exit("package '%s' is not installed in %s" %
                                      (name, prefix),
                                      json=args.json,
                                      error_type="ValueError")

    if newenv and args.clone:
        if args.packages:
            common.error_and_exit('did not expect any arguments for --clone',
                                  json=args.json,
                                  error_type="ValueError")
        clone(args.clone, prefix, json=args.json, quiet=args.quiet)
        touch_nonadmin(prefix)
        if not args.json:
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

    specs = []
    if args.file:
        specs.extend(common.specs_from_url(args.file, json=args.json))
    elif getattr(args, 'all', False):
        linked = ci.linked(prefix)
        for pkg in linked:
            name, ver, build = pkg.rsplit('-', 2)
            if name == 'python' and ver.startswith('2'):
                # Oh Python 2...
                specs.append('%s >=%s,<3' % (name, ver))
            else:
                specs.append('%s >=%s' % (name, ver))
    specs.extend(common.specs_from_args(args.packages, json=args.json))

    if command == 'install' and args.revision:
        get_revision(args.revision, json=args.json)
    else:
        common.check_specs(prefix, specs, json=args.json)

    if args.use_local:
        from conda.fetch import fetch_index
        from conda.utils import url_path
        try:
            from conda_build import config as build_config
        except ImportError:
            common.error_and_exit("you need to have 'conda-build' installed"
                                  " to use the --use-local option",
                                  json=args.json,
                                  error_type="RuntimeError")
        # remove the cache such that a refetch is made,
        # this is necessary because we add the local build repo URL
        fetch_index.cache = {}
        index = common.get_index_trap([url_path(build_config.croot)],
                                      use_cache=args.use_index_cache,
                                      unknown=args.unknown,
                                      json=args.json)
    else:
        index = common.get_index_trap(channel_urls=channel_urls, prepend=not
                                      args.override_channels,
                                      use_cache=args.use_index_cache,
                                      unknown=args.unknown,
                                      json=args.json)

    # Don't update packages that are already up-to-date
    if command == 'update' and not args.all:
        r = Resolve(index)
        orig_packages = args.packages[:]
        for name in orig_packages:
            installed_metadata = [ci.is_linked(prefix, dist)
                                  for dist in linked]
            vers_inst = [dist.rsplit('-', 2)[1] for dist in linked
                         if dist.rsplit('-', 2)[0] == name]
            build_inst = [m['build_number'] for m in installed_metadata if
                          m['name'] == name]

            try:
                assert len(vers_inst) == 1, name
                assert len(build_inst) == 1, name
            except AssertionError as e:
                if args.json:
                    common.exception_and_exit(e, json=True)
                else:
                    raise

            pkgs = sorted(r.get_pkgs(MatchSpec(name)))
            if not pkgs:
                # Shouldn't happen?
                continue
            latest = pkgs[-1]

            if latest.version == vers_inst[0] and latest.build_number == build_inst[0]:
                args.packages.remove(name)
        if not args.packages:
            from conda.cli.main_list import print_packages

            if not args.json:
                regex = '^(%s)$' % '|'.join(orig_packages)
                print('# All requested packages already installed.')
                print_packages(prefix, regex)
            else:
                common.stdout_json_success(message='All requested packages already installed.')
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
        common.error_and_exit("cannot mix specifications with conda package filenames",
                              json=args.json,
                              error_type="ValueError")

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
                common.error_and_exit("Error: could not create directory: %s" % prefix,
                                      json=args.json,
                                      error_type="OSError")
        else:
            common.error_and_exit("""\
environment does not exist: %s
#
# Use 'conda create' to create an environment before installing packages
# into it.
#""" % prefix,
                                  json=args.json,
                                  error_type="NoEnvironmentFound")

    try:
        if command == 'install' and args.revision:
            actions = plan.revert_actions(prefix, get_revision(args.revision))
        else:
            actions = plan.install_actions(prefix, index, specs, force=args.force,
                                           only_names=only_names, pinned=args.pinned, minimal_hint=args.alt_hint)
    except NoPackagesFound as e:
        error_message = e.args[0]

        packages = {index[fn]['name'] for fn in index}

        for pkg in e.pkgs:
            close = get_close_matches(pkg, packages)
            if close:
                error_message += "\n\nDid you mean one of these?\n    %s" % (', '.join(close))
            error_message += '\n\nYou can search for this package on Binstar with'
            error_message += '\n\n    binstar search -t conda %s' % pkg
            error_message += '\n\nYou may need to install the Binstar command line client with'
            error_message += '\n\n    conda install binstar'
        common.error_and_exit(error_message, json=args.json)
    except SystemExit as e:
        # Unsatisfiable package specifications/no such revision/import error
        error_type = 'UnsatisfiableSpecifications'
        if e.args and 'could not import' in e.args[0]:
            error_type = 'ImportError'
        common.exception_and_exit(e, json=args.json, newline=True,
                                  error_text=False,
                                  error_type=error_type)

    if plan.nothing_to_do(actions):
        from conda.cli.main_list import print_packages

        if not args.json:
            regex = '^(%s)$' % '|'.join(spec_names)
            print('\n# All requested packages already installed.')
            print_packages(prefix, regex)
        else:
            common.stdout_json_success(message='All requested packages already installed.')
        return

    if not args.json:
        print()
        print("Package plan for installation in environment %s:" % prefix)
        plan.display_actions(actions, index)

    if command in {'install', 'update'}:
        common.check_write(command, prefix)

    if not args.json:
        if not pscheck.main(args):
            common.confirm_yn(args)
    else:
        if (sys.platform == 'win32' and not args.force_pscheck and
            not pscheck.check_processes(verbose=False)):
            common.error_and_exit("Cannot continue operation while processes "
                                  "from packages are running without --force-pscheck.",
                                  json=True,
                                  error_type="ProcessesStillRunning")
        elif args.dry_run:
            common.stdout_json_success(actions=actions, dry_run=True)
            sys.exit(0)

    with common.json_progress_bars(json=args.json and not args.quiet):
        try:
            plan.execute_actions(actions, index, verbose=not args.quiet)
        except RuntimeError as e:
            if len(e.args) > 0 and "LOCKERROR" in e.args[0]:
                error_type = "AlreadyLocked"
            else:
                error_type = "RuntimeError"
            common.exception_and_exit(e, error_type=error_type, json=args.json)
        except SystemExit as e:
            common.exception_and_exit(e, json=args.json)

    if newenv:
        touch_nonadmin(prefix)
        if not args.json:
            print_activate(args.name if args.name else prefix)

    if args.json:
        common.stdout_json_success(actions=actions)


def check_install(packages, platform=None, channel_urls=(), prepend=True, minimal_hint=False):
    try:
        prefix = tempfile.mkdtemp('conda')
        specs = common.specs_from_args(packages)
        index = get_index(channel_urls=channel_urls, prepend=prepend,
                          platform=platform)
        plan.install_actions(prefix, index, specs, pinned=False, minimal_hint=minimal_hint)
    finally:
        ci.rm_rf(prefix)
