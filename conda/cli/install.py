# (c) Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import absolute_import, division, print_function, unicode_literals

from difflib import get_close_matches
import errno
import logging
import os
from os.path import abspath, basename, exists, isdir, join
import re

from . import common
from .find_commands import find_executable
from .._vendor.auxlib.ish import dals
from ..base.constants import ROOT_ENV_NAME
from ..base.context import context
from ..common.compat import on_win, text_type
from ..core.index import get_index
from ..core.linked_data import linked as install_linked
from ..exceptions import (CondaEnvironmentNotFoundError,
                          CondaIOError, CondaImportError, CondaOSError,
                          CondaRuntimeError, CondaSystemExit, CondaValueError,
                          DirectoryNotFoundError, DryRunExit, LockError, NoPackagesFoundError,
                          PackageNotFoundError, TooManyArgumentsError, UnsatisfiableError)
from ..misc import append_env, clone_env, explicit, touch_nonadmin
from ..models.channel import prioritize_channels
from ..plan import (display_actions, execute_actions, get_pinned_specs, install_actions_list,
                    is_root_prefix, nothing_to_do, revert_actions)

log = logging.getLogger(__name__)


def check_prefix(prefix, json=False):
    name = basename(prefix)
    error = None
    if name.startswith('.'):
        error = "environment name cannot start with '.': %s" % name
    if name == ROOT_ENV_NAME:
        error = "'%s' is a reserved environment name" % name
    if exists(prefix):
        if isdir(prefix) and 'conda-meta' not in os.listdir(prefix):
            return None
        error = "prefix already exists: %s" % prefix

    if error:
        raise CondaValueError(error, json)


def clone(src_arg, dst_prefix, json=False, quiet=False, index_args=None):
    if os.sep in src_arg:
        src_prefix = abspath(src_arg)
        if not isdir(src_prefix):
            raise DirectoryNotFoundError(src_arg, 'no such directory: %s' % src_arg, json)
    else:
        src_prefix = context.clone_src

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
    if on_win:
        message = dals("""
        #
        # To activate this environment, use:
        # > activate %s
        #
        # To deactivate this environment, use:
        # > deactivate %s
        #
        # * for power-users using bash, you must source
        #
        """)
    else:
        shell = os.path.split(os.environ.get('SHELL', ''))[-1]
        if 'fish' == shell:
            message = dals("""
            #
            # To activate this environment, use:
            # > conda activate %s
            #
            # To deactivate this environment, use:
            # > conda deactivate %s
            #
            """)
        else:
            message = dals("""
            #
            # To activate this environment, use:
            # > source activate %s
            #
            # To deactivate this environment, use:
            # > source deactivate %s
            #
            """)

    return message % (arg, arg)


def get_revision(arg, json=False):
    try:
        return int(arg)
    except ValueError:
        CondaValueError("expected revision number, not: '%s'" % arg, json)


def install(args, parser, command='install'):
    """
    conda install, conda update, and conda create
    """
    context.validate_configuration()
    newenv = bool(command == 'create')
    isupdate = bool(command == 'update')
    isinstall = bool(command == 'install')
    if newenv:
        common.ensure_name_or_prefix(args, command)
    prefix = context.prefix if newenv or args.mkdir else context.prefix_w_legacy_search
    if newenv:
        check_prefix(prefix, json=context.json)
    if context.force_32bit and is_root_prefix(prefix):
        raise CondaValueError("cannot use CONDA_FORCE_32BIT=1 in root env")
    if isupdate and not (args.file or args.all or args.packages):
        raise CondaValueError("""no package names supplied
# If you want to update to a newer version of Anaconda, type:
#
# $ conda update --prefix %s anaconda
""" % prefix)

    linked_dists = install_linked(prefix)
    linked_names = tuple(ld.quad[0] for ld in linked_dists)
    if isupdate and not args.all:
        for name in args.packages:
            common.arg2spec(name, json=context.json, update=True)
            if name not in linked_names and common.prefix_if_in_private_env(name) is None:
                raise PackageNotFoundError(name, "Package '%s' is not installed in %s" %
                                           (name, prefix))

    if newenv and not args.no_default_packages:
        default_packages = list(context.create_default_packages)
        # Override defaults if they are specified at the command line
        for default_pkg in context.create_default_packages:
            if any(pkg.split('=')[0] == default_pkg for pkg in args.packages):
                default_packages.remove(default_pkg)
        args.packages.extend(default_packages)
    else:
        default_packages = []

    common.ensure_use_local(args)
    common.ensure_override_channels_requires_channel(args)
    index_args = {
        'use_cache': args.use_index_cache,
        'channel_urls': context.channels,
        'unknown': args.unknown,
        'prepend': not args.override_channels,
        'use_local': args.use_local
    }

    specs = []
    if args.file:
        for fpath in args.file:
            specs.extend(common.specs_from_url(fpath, json=context.json))
        if '@EXPLICIT' in specs:
            explicit(specs, prefix, verbose=not context.quiet, index_args=index_args)
            return
    elif getattr(args, 'all', False):
        if not linked_dists:
            raise PackageNotFoundError('', "There are no packages installed in the "
                                       "prefix %s" % prefix)
        specs.extend(d.quad[0] for d in linked_dists)
    specs.extend(common.specs_from_args(args.packages, json=context.json))

    if isinstall and args.revision:
        get_revision(args.revision, json=context.json)
    elif isinstall and not (args.file or args.packages):
        raise CondaValueError("too few arguments, "
                              "must supply command line package specs or --file")

    num_cp = sum(s.endswith('.tar.bz2') for s in args.packages)
    if num_cp:
        if num_cp == len(args.packages):
            explicit(args.packages, prefix, verbose=not context.quiet)
            return
        else:
            raise CondaValueError("cannot mix specifications with conda package"
                                  " filenames")

    if newenv and args.clone:
        package_diff = set(args.packages) - set(default_packages)
        if package_diff:
            raise TooManyArgumentsError(0, len(package_diff), list(package_diff),
                                        'did not expect any arguments for --clone')

        clone(args.clone, prefix, json=context.json, quiet=context.quiet, index_args=index_args)
        append_env(prefix)
        touch_nonadmin(prefix)
        if not context.json and not context.quiet:
            print(print_activate(args.name if args.name else prefix))
        return

    index = get_index(channel_urls=index_args['channel_urls'],
                      prepend=index_args['prepend'], platform=None,
                      use_local=index_args['use_local'], use_cache=index_args['use_cache'],
                      unknown=index_args['unknown'], prefix=prefix)
    ospecs = list(specs)

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
                raise CondaOSError("Error: could not create directory: %s" % prefix)
        else:
            raise CondaEnvironmentNotFoundError(prefix)

    try:
        if isinstall and args.revision:
            action_set = [revert_actions(prefix, get_revision(args.revision), index)]
        else:
            with common.json_progress_bars(json=context.json and not context.quiet):
                _channel_priority_map = prioritize_channels(index_args['channel_urls'])
                action_set = install_actions_list(
                    prefix, index, specs, force=args.force, only_names=only_names,
                    pinned=args.pinned, always_copy=context.always_copy,
                    minimal_hint=args.alt_hint, update_deps=context.update_dependencies,
                    channel_priority_map=_channel_priority_map, is_update=isupdate)
    except NoPackagesFoundError as e:
        error_message = [e.args[0]]

        if isupdate and args.all:
            # Packages not found here just means they were installed but
            # cannot be found any more. Just skip them.
            if not context.json:
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

            raise PackageNotFoundError('', error_message)

    except (UnsatisfiableError, SystemExit) as e:
        # Unsatisfiable package specifications/no such revision/import error
        if e.args and 'could not import' in e.args[0]:
            raise CondaImportError(text_type(e))
        raise

    if not context.json:
        if any(nothing_to_do(actions) for actions in action_set) and not newenv:
            from .main_list import print_packages

            if not context.json:
                spec_regex = r'^(%s)$' % re.escape('|'.join(s.split()[0] for s in ospecs))
                print('\n# All requested packages already installed.')
                for action in action_set:
                    print_packages(action["PREFIX"], spec_regex)
            else:
                common.stdout_json_success(
                    message='All requested packages already installed.')
            return

        for actions in action_set:
            print()
            print("Package plan for installation in environment %s:" % actions["PREFIX"])
            display_actions(actions, index, show_channel_urls=context.show_channel_urls)
            # TODO: this is where the transactions should be instantiated
        common.confirm_yn(args)

    elif args.dry_run:
        common.stdout_json_success(actions=action_set, dry_run=True)
        raise DryRunExit()

    for actions in action_set:
        if newenv:
            # needed in the case of creating an empty env
            from ..instructions import LINK, UNLINK, SYMLINK_CONDA
            if not actions[LINK] and not actions[UNLINK]:
                actions[SYMLINK_CONDA] = [context.root_prefix]

        if command in {'install', 'update'}:
            check_write(command, prefix)

        # if not context.json:
        #     common.confirm_yn(args)
        # elif args.dry_run:
        #     common.stdout_json_success(actions=actions, dry_run=True)
        #     raise DryRunExit()

        with common.json_progress_bars(json=context.json and not context.quiet):
            try:
                execute_actions(actions, index, verbose=not context.quiet)
                if not (command == 'update' and args.all):
                    try:
                        with open(join(prefix, 'conda-meta', 'history'), 'a') as f:
                            f.write('# %s specs: %s\n' % (command, ','.join(specs)))
                    except IOError as e:
                        if e.errno == errno.EACCES:
                            log.debug("Can't write the history file")
                        else:
                            raise CondaIOError("Can't write the history file", e)

            except RuntimeError as e:
                if len(e.args) > 0 and "LOCKERROR" in e.args[0]:
                    raise LockError('Already locked: %s' % text_type(e))
                else:
                    raise CondaRuntimeError('RuntimeError: %s' % e)
            except SystemExit as e:
                raise CondaSystemExit('Exiting', e)

        if newenv:
            append_env(prefix)
            touch_nonadmin(prefix)
            if not context.json:
                print(print_activate(args.name if args.name else prefix))

        if context.json:
            common.stdout_json_success(actions=actions)


def check_write(command, prefix, json=False):
    if inroot_notwritable(prefix):
        from conda.cli.help import root_read_only
        root_read_only(command, prefix, json=json)


def inroot_notwritable(prefix):
    """
    return True if the prefix is under root and root is not writeable
    """
    return (abspath(prefix).startswith(context.root_prefix) and
            not context.root_writable)
