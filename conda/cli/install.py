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
import logging
import errno

import conda.config as config
import conda.plan as plan
import conda.misc as misc
from conda.api import get_index
from conda.cli import common
from conda.cli.find_commands import find_executable
from conda.resolve import NoPackagesFound, Unsatisfiable, Resolve
import conda.install as ci

log = logging.getLogger(__name__)

def install_tar(prefix, tar_path, verbose=False):
    if not exists(tar_path):
        sys.exit("File does not exist: %s" % tar_path)
    tmp_dir = tempfile.mkdtemp()
    t = tarfile.open(tar_path, 'r')
    t.extractall(path=tmp_dir)
    t.close()

    paths = []
    for root, dirs, files in os.walk(tmp_dir):
        for fn in files:
            if fn.endswith('.tar.bz2'):
                paths.append(join(root, fn))

    misc.explicit(paths, prefix, verbose=verbose)
    shutil.rmtree(tmp_dir)


def check_prefix(prefix, json=False):
    name = basename(prefix)
    error = None
    if name.startswith('.'):
        error = "environment name cannot start with '.': %s" % name
    if name == config.root_env_name:
        error = "'%s' is a reserved environment name" % name
    if exists(prefix):
        error = "prefix already exists: %s" % prefix

    if error:
        common.error_and_exit(error, json=json, error_type="ValueError")


def clone(src_arg, dst_prefix, json=False, quiet=False, fetch_args=None):
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
        print("Source:      %r" % src_prefix)
        print("Destination: %r" % dst_prefix)

    with common.json_progress_bars(json=json and not quiet):
        actions, untracked_files = misc.clone_env(src_prefix, dst_prefix,
                                                  verbose=not json,
                                                  quiet=quiet,
                                                  fetch_args=fetch_args)

    if json:
        common.stdout_json_success(
            actions=actions,
            untracked_files=list(untracked_files),
            src_prefix=src_prefix,
            dst_prefix=dst_prefix
        )


def print_activate(arg):
    from conda.utils import find_parent_shell
    print("#")
    print("# To activate this environment, use:")
    if find_parent_shell() in ["powershell.exe", "cmd.exe"]:
        print("# > activate %s" % arg)
        print("#")
        print("# To deactivate this environment, use:")
        print("# > deactivate")
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
    isupdate = bool(command == 'update')
    isinstall = bool(command == 'install')
    if newenv:
        common.ensure_name_or_prefix(args, command)
    prefix = common.get_prefix(args, search=not newenv)
    if newenv:
        check_prefix(prefix, json=args.json)
    if config.force_32bit and plan.is_root_prefix(prefix):
        common.error_and_exit("cannot use CONDA_FORCE_32BIT=1 in root env")

    if isupdate and not (args.file or args.all or args.packages):
        common.error_and_exit("""no package names supplied
# If you want to update to a newer version of Anaconda, type:
#
# $ conda update --prefix %s anaconda
""" % prefix,
                              json=args.json,
                              error_type="ValueError")

    linked = ci.linked(prefix)
    lnames = {ci.name_dist(d) for d in linked}
    if isupdate and not args.all:
        for name in args.packages:
            common.arg2spec(name, json=args.json, update=True)
            if name not in lnames:
                common.error_and_exit("Package '%s' is not installed in %s" %
                                      (name, prefix),
                                      json=args.json,
                                      error_type="ValueError")

    if newenv and not args.no_default_packages:
        default_packages = config.create_default_packages[:]
        # Override defaults if they are specified at the command line
        for default_pkg in config.create_default_packages:
            if any(pkg.split('=')[0] == default_pkg for pkg in args.packages):
                default_packages.remove(default_pkg)
        args.packages.extend(default_packages)
    else:
        default_packages = []

    common.ensure_use_local(args)
    common.ensure_override_channels_requires_channel(args)
    channel_urls = args.channel or ()

    specs = []
    if args.file:
        for fpath in args.file:
            specs.extend(common.specs_from_url(fpath, json=args.json))
        if '@EXPLICIT' in specs:
            misc.explicit(specs, prefix, verbose=not args.quiet)
            return
    elif getattr(args, 'all', False):
        if not linked:
            common.error_and_exit("There are no packages installed in the "
                                  "prefix %s" % prefix)
        specs.extend(nm for nm in lnames)
    specs.extend(common.specs_from_args(args.packages, json=args.json))

    if isinstall and args.revision:
        get_revision(args.revision, json=args.json)
    elif not (newenv and args.clone):
        common.check_specs(prefix, specs, json=args.json,
                           create=(command == 'create'))

    num_cp = sum(s.endswith('.tar.bz2') for s in args.packages)
    if num_cp:
        if num_cp == len(args.packages):
            misc.explicit(args.packages, prefix, verbose=not args.quiet)
            return
        else:
            common.error_and_exit(
                "cannot mix specifications with conda package filenames",
                json=args.json,
                error_type="ValueError")

    # handle tar file containing conda packages
    if len(args.packages) == 1:
        tar_path = args.packages[0]
        if tar_path.endswith('.tar'):
            install_tar(prefix, tar_path, verbose=not args.quiet)
            return

    if newenv and args.clone:
        if set(args.packages) - set(default_packages):
            common.error_and_exit('did not expect any arguments for --clone',
                                  json=args.json,
                                  error_type="ValueError")
        clone(args.clone, prefix, json=args.json, quiet=args.quiet,
              fetch_args={'use_cache': args.use_index_cache,
                          'unknown': args.unknown})
        misc.append_env(prefix)
        misc.touch_nonadmin(prefix)
        if not args.json:
            print_activate(args.name if args.name else prefix)
        return

    index = common.get_index_trap(channel_urls=channel_urls,
                                  prepend=not args.override_channels,
                                  use_local=args.use_local,
                                  use_cache=args.use_index_cache,
                                  unknown=args.unknown,
                                  json=args.json,
                                  offline=args.offline,
                                  prefix=prefix)
    r = Resolve(index)
    ospecs = list(specs)
    plan.add_defaults_to_specs(r, linked, specs, update=isupdate)

    # Don't update packages that are already up-to-date
    if isupdate and not (args.all or args.force):
        orig_packages = args.packages[:]
        installed_metadata = [ci.is_linked(prefix, dist) for dist in linked]
        for name in orig_packages:
            vers_inst = [m['version'] for m in installed_metadata if m['name'] == name]
            build_inst = [m['build_number'] for m in installed_metadata if m['name'] == name]

            try:
                assert len(vers_inst) == 1, name
                assert len(build_inst) == 1, name
            except AssertionError as e:
                if args.json:
                    common.exception_and_exit(e, json=True)
                else:
                    raise

            pkgs = sorted(r.get_pkgs(name))
            if not pkgs:
                # Shouldn't happen?
                continue
            latest = pkgs[-1]

            if (latest.version == vers_inst[0] and
                    latest.build_number == build_inst[0]):
                args.packages.remove(name)
        if not args.packages:
            from conda.cli.main_list import print_packages

            if not args.json:
                regex = '^(%s)$' % '|'.join(orig_packages)
                print('# All requested packages already installed.')
                print_packages(prefix, regex)
            else:
                common.stdout_json_success(
                    message='All requested packages already installed.')
            return

    if args.force:
        args.no_deps = True

    if args.no_deps:
        only_names = set(s.split()[0] for s in specs)
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
        if isinstall and args.revision:
            actions = plan.revert_actions(prefix, get_revision(args.revision))
        else:
            with common.json_progress_bars(json=args.json and not args.quiet):
                actions = plan.install_actions(prefix, index, specs,
                                               force=args.force,
                                               only_names=only_names,
                                               pinned=args.pinned,
                                               always_copy=args.copy,
                                               minimal_hint=args.alt_hint,
                                               update_deps=args.update_deps)
    except NoPackagesFound as e:
        error_message = e.args[0]

        if isupdate and args.all:
            # Packages not found here just means they were installed but
            # cannot be found any more. Just skip them.
            if not args.json:
                print("Warning: %s, skipping" % error_message)
            else:
                # Not sure what to do here
                pass
            args._skip = getattr(args, '_skip', ['anaconda'])
            for pkg in e.pkgs:
                p = pkg.split()[0]
                if p in args._skip:
                    # Avoid infinite recursion. This can happen if a spec
                    # comes from elsewhere, like --file
                    raise
                args._skip.append(p)

            return install(args, parser, command=command)
        else:
            packages = {index[fn]['name'] for fn in index}

            for pkg in e.pkgs:
                close = get_close_matches(pkg, packages, cutoff=0.7)
                if close:
                    error_message += ("\n\nDid you mean one of these?"
                                      "\n\n    %s" % (', '.join(close)))
            error_message += '\n\nYou can search for this package on anaconda.org with'
            error_message += '\n\n    anaconda search -t conda %s' % pkg
            if len(e.pkgs) > 1:
                # Note this currently only happens with dependencies not found
                error_message += '\n\n (and similarly for the other packages)'

            if not find_executable('anaconda', include_others=False):
                error_message += '\n\nYou may need to install the anaconda-client'
                error_message += ' command line client with'
                error_message += '\n\n    conda install anaconda-client'

            pinned_specs = plan.get_pinned_specs(prefix)
            if pinned_specs:
                path = join(prefix, 'conda-meta', 'pinned')
                error_message += "\n\nNote that you have pinned specs in %s:" % path
                error_message += "\n\n    %r" % pinned_specs

            common.error_and_exit(error_message, json=args.json)
    except (Unsatisfiable, SystemExit) as e:
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
            regex = '^(%s)$' % '|'.join(s.split()[0] for s in ospecs)
            print('\n# All requested packages already installed.')
            print_packages(prefix, regex)
        else:
            common.stdout_json_success(
                message='All requested packages already installed.')
        return

    if not args.json:
        print()
        print("Package plan for installation in environment %s:" % prefix)
        plan.display_actions(actions, index, show_channel_urls=args.show_channel_urls)

    if command in {'install', 'update'}:
        common.check_write(command, prefix)

    if not args.json:
        common.confirm_yn(args)
    elif args.dry_run:
        common.stdout_json_success(actions=actions, dry_run=True)
        sys.exit(0)

    with common.json_progress_bars(json=args.json and not args.quiet):
        try:
            plan.execute_actions(actions, index, verbose=not args.quiet)
            if not (command == 'update' and args.all):
                try:
                    with open(join(prefix, 'conda-meta', 'history'), 'a') as f:
                        f.write('# %s specs: %s\n' % (command, ','.join(specs)))
                except IOError as e:
                    if e.errno == errno.EACCES:
                        log.debug("Can't write the history file")
                    else:
                        raise

        except RuntimeError as e:
            if len(e.args) > 0 and "LOCKERROR" in e.args[0]:
                error_type = "AlreadyLocked"
            else:
                error_type = "RuntimeError"
            common.exception_and_exit(e, error_type=error_type, json=args.json)
        except SystemExit as e:
            common.exception_and_exit(e, json=args.json)

    if newenv:
        misc.append_env(prefix)
        misc.touch_nonadmin(prefix)
        if not args.json:
            print_activate(args.name if args.name else prefix)

    if args.json:
        common.stdout_json_success(actions=actions)


def check_install(packages, platform=None, channel_urls=(), prepend=True,
                  minimal_hint=False):
    try:
        prefix = tempfile.mkdtemp('conda')
        specs = common.specs_from_args(packages)
        index = get_index(channel_urls=channel_urls, prepend=prepend,
                          platform=platform, prefix=prefix)
        linked = ci.linked(prefix)
        plan.add_defaults_to_specs(Resolve(index), linked, specs)
        actions = plan.install_actions(prefix, index, specs, pinned=False,
                                       minimal_hint=minimal_hint)
        plan.display_actions(actions, index)
        return actions
    finally:
        ci.rm_rf(prefix)
