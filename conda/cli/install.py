# (c) Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
import os
from os.path import abspath, basename, exists, isdir

from . import common
from .._vendor.auxlib.ish import dals
from ..base.constants import ROOT_ENV_NAME
from ..base.context import context
from ..common.compat import text_type
from ..core.envs_manager import EnvsDirectory
from ..core.index import get_channel_priority_map, get_index
from ..core.solve import Solver
from ..exceptions import (CondaImportError, CondaOSError, CondaSystemExit, CondaValueError,
                          DirectoryNotFoundError, DryRunExit, EnvironmentLocationNotFound,
                          PackagesNotFoundError, TooManyArgumentsError,
                          UnsatisfiableError)
from ..misc import append_env, clone_env, explicit, touch_nonadmin
from ..plan import (revert_actions)
from ..resolve import ResolvePackageNotFound

log = getLogger(__name__)
stderrlog = getLogger('conda.stderr')


def check_prefix(prefix, json=False):
    name = basename(prefix)
    error = None
    if name == ROOT_ENV_NAME:
        error = "'%s' is a reserved environment name" % name
    if exists(prefix):
        if isdir(prefix) and 'conda-meta' not in os.listdir(prefix):
            return None
        error = "prefix already exists: %s" % prefix

    if error:
        raise CondaValueError(error, json)

    if ' ' in prefix:
        stderrlog.warn("WARNING: A space was detected in your requested environment path\n"
                       "'%s'\n"
                       "Spaces in paths can sometimes be problematic." % prefix)


def clone(src_arg, dst_prefix, json=False, quiet=False, index_args=None):
    if os.sep in src_arg:
        src_prefix = abspath(src_arg)
        if not isdir(src_prefix):
            raise DirectoryNotFoundError(src_arg)
    else:
        assert context._argparse_args.clone is not None
        src_prefix = EnvsDirectory.locate_prefix_by_name(context._argparse_args.clone)

    if not json:
        print("Source:      %s" % src_prefix)
        print("Destination: %s" % dst_prefix)

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


def print_activate(env_name_or_prefix):  # pragma: no cover
    if not context.quiet and not context.json:
        message = dals("""

        To activate this environment, use

            $ conda activate %s

        To deactivate an active environment, use

            $ conda deactivate
        """) % env_name_or_prefix
        print(message)  # TODO: use logger


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
    prefix = context.target_prefix
    if newenv:
        check_prefix(prefix, json=context.json)
    if context.force_32bit and prefix == context.root_prefix:
        raise CondaValueError("cannot use CONDA_FORCE_32BIT=1 in root env")
    if isupdate and not (args.file or args.all or args.packages):
        raise CondaValueError("""no package names supplied
# If you want to update to a newer version of Anaconda, type:
#
# $ conda update --prefix %s anaconda
""" % prefix)

    args_packages = [s.strip('"\'') for s in args.packages]

    if newenv and not args.no_default_packages:
        # Override defaults if they are specified at the command line
        # TODO: rework in 4.4 branch using MatchSpec
        args_packages_names = [pkg.replace(' ', '=').split('=', 1)[0] for pkg in args_packages]
        for default_pkg in context.create_default_packages:
            default_pkg_name = default_pkg.replace(' ', '=').split('=', 1)[0]
            if default_pkg_name not in args_packages_names:
                args_packages.append(default_pkg)

    common.ensure_use_local(args)
    common.ensure_override_channels_requires_channel(args)
    index_args = {
        'use_cache': args.use_index_cache,
        'channel_urls': context.channels,
        'unknown': args.unknown,
        'prepend': not args.override_channels,
        'use_local': args.use_local
    }

    num_cp = sum(s.endswith('.tar.bz2') for s in args_packages)
    if num_cp:
        if num_cp == len(args_packages):
            explicit(args_packages, prefix, verbose=not context.quiet)
            return
        else:
            raise CondaValueError("cannot mix specifications with conda package"
                                  " filenames")

    specs = []
    if args.file:
        for fpath in args.file:
            specs.extend(common.specs_from_url(fpath, json=context.json))
        if '@EXPLICIT' in specs:
            explicit(specs, prefix, verbose=not context.quiet, index_args=index_args)
            return
    specs.extend(common.specs_from_args(args_packages, json=context.json))

    if isinstall and args.revision:
        get_revision(args.revision, json=context.json)
    elif isinstall and not (args.file or args_packages):
        raise CondaValueError("too few arguments, "
                              "must supply command line package specs or --file")

    if newenv and args.clone:
        if args.packages:
            raise TooManyArgumentsError(0, len(args.packages), list(args.packages),
                                        'did not expect any arguments for --clone')

        clone(args.clone, prefix, json=context.json, quiet=context.quiet, index_args=index_args)
        append_env(prefix)
        touch_nonadmin(prefix)
        print_activate(args.name if args.name else prefix)
        return

    if not isdir(prefix) and not newenv:
        if args.mkdir:
            try:
                os.makedirs(prefix)
            except OSError:
                raise CondaOSError("Error: could not create directory: %s" % prefix)
        else:
            raise EnvironmentLocationNotFound(prefix)

    try:
        if isinstall and args.revision:
            index = get_index(channel_urls=index_args['channel_urls'],
                              prepend=index_args['prepend'], platform=None,
                              use_local=index_args['use_local'], use_cache=index_args['use_cache'],
                              unknown=index_args['unknown'], prefix=prefix)
            unlink_link_transaction = revert_actions(prefix, get_revision(args.revision), index)
            progressive_fetch_extract = unlink_link_transaction.get_pfe()
        else:
            solver = Solver(prefix, context.channels, context.subdirs, specs_to_add=specs)
            unlink_link_transaction = solver.solve_for_transaction(
                force_reinstall=context.force,
            )
            progressive_fetch_extract = unlink_link_transaction.get_pfe()

    except ResolvePackageNotFound as e:
        channel_priority_map = get_channel_priority_map(
            channel_urls=index_args['channel_urls'],
            prepend=index_args['prepend'],
            platform=None,
            use_local=index_args['use_local'],
        )
        channels_urls = tuple(channel_priority_map)
        raise PackagesNotFoundError(e.bad_deps, channels_urls)

    except (UnsatisfiableError, SystemExit) as e:
        # Unsatisfiable package specifications/no such revision/import error
        if e.args and 'could not import' in e.args[0]:
            raise CondaImportError(text_type(e))
        raise

    handle_txn(progressive_fetch_extract, unlink_link_transaction, prefix, args, newenv)


def handle_txn(progressive_fetch_extract, unlink_link_transaction, prefix, args, newenv,
               remove_op=False):
    if unlink_link_transaction.nothing_to_do:
        if remove_op:
            # No packages found to remove from environment
            raise PackagesNotFoundError(args.package_names)
        elif not newenv:
            if context.json:
                common.stdout_json_success(message='All requested packages already installed.')
            else:
                print('\n# All requested packages already installed.\n')
            return

    if not context.json:
        unlink_link_transaction.display_actions(progressive_fetch_extract)
        common.confirm_yn()

    elif context.dry_run:
        common.stdout_json_success(unlink_link_transaction=unlink_link_transaction, prefix=prefix,
                                   dry_run=True)
        raise DryRunExit()

    try:
        progressive_fetch_extract.execute()
        unlink_link_transaction.execute()

    except SystemExit as e:
        raise CondaSystemExit('Exiting', e)

    if newenv:
        append_env(prefix)
        touch_nonadmin(prefix)
        print_activate(args.name if args.name else prefix)

    if context.json:
        actions = unlink_link_transaction.make_legacy_action_groups(progressive_fetch_extract)[0]
        common.stdout_json_success(actions=actions)
