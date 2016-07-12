# (c) Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import errno
import logging
import os
import shutil
import tarfile
import tempfile
from difflib import get_close_matches
from os.path import isdir, join, basename, exists, abspath

from conda.api import get_index
from ..cli import common
from ..cli.find_commands import find_executable
from ..config import create_default_packages, force_32bit, root_env_name
from ..exceptions import (CondaFileNotFoundError, CondaValueError, DirectoryNotFoundError,
                          CondaEnvironmentError, PackageNotFoundError, TooManyArgumentsError,
                          CondaAssertionError, CondaOSError, CondaImportError,
                          CondaError, DryRunExit, LockError, CondaRuntimeError,
                          CondaSystemExit, NoPackagesFoundError, UnsatisfiableError, CondaIOError)
from ..install import linked as install_linked
from ..install import name_dist, is_linked
from ..misc import explicit, clone_env, append_env, touch_nonadmin
from ..plan import (is_root_prefix, get_pinned_specs, install_actions, add_defaults_to_specs,
                    display_actions, revert_actions, nothing_to_do, execute_actions)
from ..resolve import Resolve
from ..utils import find_parent_shell
from .. import config

log = logging.getLogger(__name__)


def install_tar(prefix, tar_path, verbose=False):
    if not exists(tar_path):
        raise CondaFileNotFoundError(tar_path)
    tmp_dir = tempfile.mkdtemp()
    t = tarfile.open(tar_path, 'r')
    t.extractall(path=tmp_dir)
    t.close()

    paths = []
    for root, dirs, files in os.walk(tmp_dir):
        for fn in files:
            if fn.endswith('.tar.bz2'):
                paths.append(join(root, fn))

    explicit(paths, prefix, verbose=verbose)
    shutil.rmtree(tmp_dir)


def check_prefix(prefix, json=False):
    name = basename(prefix)
    error = None
    if name.startswith('.'):
        error = "environment name cannot start with '.': %s" % name
    if name == root_env_name:
        error = "'%s' is a reserved environment name" % name
    if exists(prefix):
        if isdir(prefix) and not os.listdir(prefix):
            return None
        error = "prefix already exists: %s" % prefix

    if error:
        raise CondaValueError(error, json)


def clone(src_arg, dst_prefix, json=False, quiet=False, index_args=None):
    if os.sep in src_arg:
        src_prefix = abspath(src_arg)
        if not isdir(src_prefix):
            raise DirectoryNotFoundError('no such directory: %s' % src_arg, json)
    else:
        src_prefix = common.find_prefix_name(src_arg)
        if src_prefix is None:
            raise CondaEnvironmentError('could not find environment: %s' %
                                        src_arg, json)

    if not json:
        print("Source:      %s" % src_prefix)
        print("Destination: %s" % dst_prefix)

    with common.json_progress_bars(json=json and not quiet):
        actions, untracked_files = clone_env(src_prefix, dst_prefix,
                                             verbose=not json,
                                             quiet=quiet,
                                             index_args=index_args)

    if json:
        common.stdout_json_success(
            actions=actions,
            untracked_files=list(untracked_files),
            src_prefix=src_prefix,
            dst_prefix=dst_prefix
        )


def print_activate(arg):
    shell = find_parent_shell(path=False)
    print("#")
    print("# To activate this environment, use:")
    if shell in ["powershell.exe", "cmd.exe"]:
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
        CondaValueError("expected revision number, not: '%s'" % arg, json)


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
    if force_32bit and is_root_prefix(prefix):
        raise CondaValueError("cannot use CONDA_FORCE_32BIT=1 in root env")
    if isupdate and not (args.file or args.all or args.packages):
        raise CondaValueError("""no package names supplied
# If you want to update to a newer version of Anaconda, type:
#
# $ conda update --prefix %s anaconda
""" % prefix, args.json)

    linked = install_linked(prefix)
    lnames = {name_dist(d) for d in linked}
    if isupdate and not args.all:
        for name in args.packages:
            common.arg2spec(name, json=args.json, update=True)
            if name not in lnames:
                raise PackageNotFoundError("Package '%s' is not installed in %s" %
                                           (name, prefix), args.json)

    if newenv and not args.no_default_packages:
        default_packages = create_default_packages[:]
        # Override defaults if they are specified at the command line
        for default_pkg in create_default_packages:
            if any(pkg.split('=')[0] == default_pkg for pkg in args.packages):
                default_packages.remove(default_pkg)
        args.packages.extend(default_packages)
    else:
        default_packages = []

    common.ensure_use_local(args)
    common.ensure_override_channels_requires_channel(args)
    index_args = {
        'use_cache': args.use_index_cache,
        'channel_urls': args.channel or (),
        'unknown': args.unknown,
        'prepend': not args.override_channels,
        'use_local': args.use_local
    }

    specs = []
    if args.file:
        for fpath in args.file:
            specs.extend(common.specs_from_url(fpath, json=args.json))
        if '@EXPLICIT' in specs:
            explicit(specs, prefix, verbose=not args.quiet, index_args=index_args)
            return
    elif getattr(args, 'all', False):
        if not linked:
            raise PackageNotFoundError("There are no packages installed in the "
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
            explicit(args.packages, prefix, verbose=not args.quiet)
            return
        else:
            raise CondaValueError("cannot mix specifications with conda package"
                                  " filenames", args.json)

    # handle tar file containing conda packages
    if len(args.packages) == 1:
        tar_path = args.packages[0]
        if tar_path.endswith('.tar'):
            install_tar(prefix, tar_path, verbose=not args.quiet)
            return

    if newenv and args.clone:
        if set(args.packages) - set(default_packages):
            raise TooManyArgumentsError('did not expect any arguments for'
                                        '--clone', args.json)

        clone(args.clone, prefix, json=args.json, quiet=args.quiet, index_args=index_args)
        append_env(prefix)
        touch_nonadmin(prefix)
        if not args.json:
            print_activate(args.name if args.name else prefix)
        return

    index = get_index(channel_urls=index_args['channel_urls'], prepend=index_args['prepend'],
                      platform=None, use_local=index_args['use_local'],
                      use_cache=index_args['use_cache'], unknown=index_args['unknown'],
                      prefix=prefix)
    r = Resolve(index)
    ospecs = list(specs)
    add_defaults_to_specs(r, linked, specs, update=isupdate)

    # Don't update packages that are already up-to-date
    if isupdate and not (args.all or args.force):
        orig_packages = args.packages[:]
        installed_metadata = [is_linked(prefix, dist) for dist in linked]
        for name in orig_packages:
            vers_inst = [m['version'] for m in installed_metadata if m['name'] == name]
            build_inst = [m['build_number'] for m in installed_metadata if m['name'] == name]

            try:
                assert len(vers_inst) == 1, name
                assert len(build_inst) == 1, name
            except AssertionError as e:
                raise CondaAssertionError('', e, args.json)

            pkgs = sorted(r.get_pkgs(name))
            if not pkgs:
                # Shouldn't happen?
                continue
            latest = pkgs[-1]

            if (latest.version == vers_inst[0] and
                    latest.build_number == build_inst[0]):
                args.packages.remove(name)
        if not args.packages:
            from .main_list import print_packages

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
        only_names = set(s.split()[0] for s in ospecs)
    else:
        only_names = None

    if not isdir(prefix) and not newenv:
        if args.mkdir:
            try:
                os.makedirs(prefix)
            except OSError:
                raise CondaOSError("Error: could not create directory: %s" %
                                   prefix, args.json)
        else:
            raise CondaEnvironmentError("""\
environment does not exist: %s
#
# Use 'conda create' to create an environment before installing packages
# into it.
#""" % prefix, args.json)

    if hasattr(args, 'shortcuts'):
        config.shortcuts = args.shortcuts and config.shortcuts

    try:
        if isinstall and args.revision:
            actions = revert_actions(prefix, get_revision(args.revision))
        else:
            with common.json_progress_bars(json=args.json and not args.quiet):
                actions = install_actions(prefix, index, specs,
                                          force=args.force,
                                          only_names=only_names,
                                          pinned=args.pinned,
                                          always_copy=args.copy,
                                          minimal_hint=args.alt_hint,
                                          update_deps=args.update_deps)
    except NoPackagesFoundError as e:
        error_message = [e.args[0]]

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

            nfound = 0
            for pkg in sorted(e.pkgs):
                pkg = pkg.split()[0]
                if pkg in packages:
                    continue
                close = get_close_matches(pkg, packages, cutoff=0.7)
                if not close:
                    continue
                if nfound == 0:
                    error_message.append("\n\nClose matches found; did you mean one of these?\n")
                error_message.append("\n    %s: %s" % (pkg, ', '.join(close)))
                nfound += 1
            error_message.append('\n\nYou can search for packages on anaconda.org with')
            error_message.append('\n\n    anaconda search -t conda %s' % pkg)
            if len(e.pkgs) > 1:
                # Note this currently only happens with dependencies not found
                error_message.append('\n\n(and similarly for the other packages)')

            if not find_executable('anaconda', include_others=False):
                error_message.append('\n\nYou may need to install the anaconda-client')
                error_message.append(' command line client with')
                error_message.append('\n\n    conda install anaconda-client')

            pinned_specs = get_pinned_specs(prefix)
            if pinned_specs:
                path = join(prefix, 'conda-meta', 'pinned')
                error_message.append("\n\nNote that you have pinned specs in %s:" % path)
                error_message.append("\n\n    %r" % pinned_specs)

            error_message = ''.join(error_message)

            raise PackageNotFoundError(error_message, args.json)

    except (UnsatisfiableError, SystemExit) as e:
        # Unsatisfiable package specifications/no such revision/import error
        if e.args and 'could not import' in e.args[0]:
            raise CondaImportError('', e, args.json)
        raise CondaError('UnsatisfiableSpecifications', e, args.json)

    if nothing_to_do(actions):
        from .main_list import print_packages

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
        display_actions(actions, index, show_channel_urls=args.show_channel_urls)

    if command in {'install', 'update'}:
        common.check_write(command, prefix)

    if not args.json:
        common.confirm_yn(args)
    elif args.dry_run:
        common.stdout_json_success(actions=actions, dry_run=True)
        raise DryRunExit

    with common.json_progress_bars(json=args.json and not args.quiet):
        try:
            execute_actions(actions, index, verbose=not args.quiet)
            if not (command == 'update' and args.all):
                try:
                    with open(join(prefix, 'conda-meta', 'history'), 'a') as f:
                        f.write('# %s specs: %s\n' % (command, specs))
                except IOError as e:
                    if e.errno == errno.EACCES:
                        log.debug("Can't write the history file")
                    else:
                        raise CondaIOError("Can't write the history file")

        except RuntimeError as e:
            if len(e.args) > 0 and "LOCKERROR" in e.args[0]:
                raise LockError('Already locked', e, args.json)
            else:
                raise CondaRuntimeError('RuntimeError', e, args.json)
        except SystemExit as e:
            raise CondaSystemExit('Exiting', e, args.json)

    if newenv:
        append_env(prefix)
        touch_nonadmin(prefix)
        if not args.json:
            print_activate(args.name if args.name else prefix)

    if args.json:
        common.stdout_json_success(actions=actions)
