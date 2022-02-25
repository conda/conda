# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import timedelta
from errno import ENOSPC
from functools import partial
import json
from logging import getLogger
import os
from os.path import join
import sys
from textwrap import dedent
from traceback import format_exception, format_exception_only
import getpass

from . import CondaError, CondaExitZero, CondaMultiError, text_type
from .auxlib.entity import EntityEncoder
from .auxlib.ish import dals
from .auxlib.type_coercion import boolify
from ._vendor.toolz import groupby
from .base.constants import COMPATIBLE_SHELLS, PathConflict, SafetyChecks
from .common.compat import PY2, ensure_text_type, input, iteritems, iterkeys, on_win, string_types
from .common.io import dashlist, timeout
from .common.signals import get_signal_name

log = getLogger(__name__)


# TODO: for conda-build compatibility only
# remove in conda 4.4
class ResolvePackageNotFound(CondaError):
    def __init__(self, bad_deps):
        # bad_deps is a list of lists
        # bad_deps should really be named 'invalid_chains'
        self.bad_deps = tuple(dep for deps in bad_deps for dep in deps if dep)
        formatted_chains = tuple(" -> ".join(map(str, bad_chain)) for bad_chain in bad_deps)
        self._formatted_chains = formatted_chains
        message = '\n' + '\n'.join(('  - %s' % bad_chain) for bad_chain in formatted_chains)
        super(ResolvePackageNotFound, self).__init__(message)
NoPackagesFound = NoPackagesFoundError = ResolvePackageNotFound  # NOQA


class LockError(CondaError):
    def __init__(self, message):
        msg = "%s" % message
        super(LockError, self).__init__(msg)


class ArgumentError(CondaError):
    return_code = 2

    def __init__(self, message, **kwargs):
        super(ArgumentError, self).__init__(message, **kwargs)


class CommandArgumentError(ArgumentError):
    # TODO: Consolidate with ArgumentError.
    return_code = 2

    def __init__(self, message, **kwargs):
        command = ' '.join(ensure_text_type(s) for s in sys.argv)
        super(CommandArgumentError, self).__init__(message, command=command, **kwargs)


class Help(CondaError):
    pass


class ActivateHelp(Help):

    def __init__(self):
        message = dals("""
        usage: conda activate [-h] [--[no-]stack] [env_name_or_prefix]

        Activate a conda environment.

        Options:

        positional arguments:
          env_name_or_prefix    The environment name or prefix to activate. If the
                                prefix is a relative path, it must start with './'
                                (or '.\\' on Windows).

        optional arguments:
          -h, --help            Show this help message and exit.
          --stack               Stack the environment being activated on top of the
                                previous active environment, rather replacing the
                                current active environment with a new one. Currently,
                                only the PATH environment variable is stacked. This
                                may be enabled implicitly by the 'auto_stack'
                                configuration variable.
          --no-stack            Do not stack the environment. Overrides 'auto_stack'
                                setting.
        """)
        super(ActivateHelp, self).__init__(message)


class DeactivateHelp(Help):

    def __init__(self):
        message = dals("""
        usage: conda deactivate [-h]

        Deactivate the current active conda environment.

        Options:

        optional arguments:
          -h, --help            Show this help message and exit.
        """)
        super(DeactivateHelp, self).__init__(message)


class GenericHelp(Help):

    def __init__(self, command):
        message = "help requested for %s" % command
        super(GenericHelp, self).__init__(message)


class CondaSignalInterrupt(CondaError):
    def __init__(self, signum):
        signal_name = get_signal_name(signum)
        super(CondaSignalInterrupt, self).__init__("Signal interrupt %(signal_name)s",
                                                   signal_name=signal_name,
                                                   signum=signum)


class TooManyArgumentsError(ArgumentError):
    def __init__(self, expected, received, offending_arguments, optional_message='',
                 *args):
        self.expected = expected
        self.received = received
        self.offending_arguments = offending_arguments
        self.optional_message = optional_message

        suffix = 's' if received - expected > 1 else ''
        msg = ('%s Got %s argument%s (%s) but expected %s.' %
               (optional_message, received, suffix, ', '.join(offending_arguments), expected))
        super(TooManyArgumentsError, self).__init__(msg, *args)


class TooFewArgumentsError(ArgumentError):
    def __init__(self, expected, received, optional_message='', *args):
        self.expected = expected
        self.received = received
        self.optional_message = optional_message

        msg = ('%s Got %s arguments but expected %s.' %
               (optional_message, received, expected))
        super(TooFewArgumentsError, self).__init__(msg, *args)


class ClobberError(CondaError):
    def __init__(self, message, path_conflict, **kwargs):
        self.path_conflict = path_conflict
        super(ClobberError, self).__init__(message, **kwargs)

    def __repr__(self):
        clz_name = "ClobberWarning" if self.path_conflict == PathConflict.warn else "ClobberError"
        return '%s: %s\n' % (clz_name, self)


class BasicClobberError(ClobberError):
    def __init__(self, source_path, target_path, context):
        message = dals("""
        Conda was asked to clobber an existing path.
          source path: %(source_path)s
          target path: %(target_path)s
        """)
        if context.path_conflict == PathConflict.prevent:
            message += ("Conda no longer clobbers existing paths without the use of the "
                        "--clobber option\n.")
        super(BasicClobberError, self).__init__(message, context.path_conflict,
                                                target_path=target_path,
                                                source_path=source_path)


class KnownPackageClobberError(ClobberError):
    def __init__(self, target_path, colliding_dist_being_linked, colliding_linked_dist, context):
        message = dals("""
        The package '%(colliding_dist_being_linked)s' cannot be installed due to a
        path collision for '%(target_path)s'.
        This path already exists in the target prefix, and it won't be removed by
        an uninstall action in this transaction. The path appears to be coming from
        the package '%(colliding_linked_dist)s', which is already installed in the prefix.
        """)
        if context.path_conflict == PathConflict.prevent:
            message += ("If you'd like to proceed anyway, re-run the command with "
                        "the `--clobber` flag.\n.")
        super(KnownPackageClobberError, self).__init__(
            message, context.path_conflict,
            target_path=target_path,
            colliding_dist_being_linked=colliding_dist_being_linked,
            colliding_linked_dist=colliding_linked_dist,
        )


class UnknownPackageClobberError(ClobberError):
    def __init__(self, target_path, colliding_dist_being_linked, context):
        message = dals("""
        The package '%(colliding_dist_being_linked)s' cannot be installed due to a
        path collision for '%(target_path)s'.
        This path already exists in the target prefix, and it won't be removed
        by an uninstall action in this transaction. The path is one that conda
        doesn't recognize. It may have been created by another package manager.
        """)
        if context.path_conflict == PathConflict.prevent:
            message += ("If you'd like to proceed anyway, re-run the command with "
                        "the `--clobber` flag.\n.")
        super(UnknownPackageClobberError, self).__init__(
            message, context.path_conflict,
            target_path=target_path,
            colliding_dist_being_linked=colliding_dist_being_linked,
        )


class SharedLinkPathClobberError(ClobberError):
    def __init__(self, target_path, incompatible_package_dists, context):
        message = dals("""
        This transaction has incompatible packages due to a shared path.
          packages: %(incompatible_packages)s
          path: '%(target_path)s'
        """)
        if context.path_conflict == PathConflict.prevent:
            message += ("If you'd like to proceed anyway, re-run the command with "
                        "the `--clobber` flag.\n.")
        super(SharedLinkPathClobberError, self).__init__(
            message, context.path_conflict,
            target_path=target_path,
            incompatible_packages=', '.join(text_type(d) for d in incompatible_package_dists),
        )


class CommandNotFoundError(CondaError):
    def __init__(self, command):
        activate_commands = {
            'activate',
            'deactivate',
            'run',
        }
        conda_commands = {
            'clean',
            'config',
            'create',
            'help',
            'info',
            'install',
            'list',
            'package',
            'remove',
            'search',
            'uninstall',
            'update',
            'upgrade',
        }
        build_commands = {
            'build',
            'convert',
            'develop',
            'index',
            'inspect',
            'metapackage',
            'render',
            'skeleton',
        }
        from .base.context import context
        from .cli.main import init_loggers
        init_loggers(context)
        if command in activate_commands:
            # TODO: Point users to a page at conda-docs, which explains this context in more detail
            builder = ["Your shell has not been properly configured to use 'conda %(command)s'."]
            if on_win:
                builder.append(dals("""
                If using 'conda %(command)s' from a batch script, change your
                invocation to 'CALL conda.bat %(command)s'.
                """))
            builder.append(dals("""
            To initialize your shell, run

                $ conda init <SHELL_NAME>

            Currently supported shells are:%(supported_shells)s

            See 'conda init --help' for more information and options.

            IMPORTANT: You may need to close and restart your shell after running 'conda init'.
            """) % {
                'supported_shells': dashlist(COMPATIBLE_SHELLS),
            })
            message = '\n'.join(builder)
        elif command in build_commands:
            message = "To use 'conda %(command)s', install conda-build."
        else:
            from difflib import get_close_matches
            from .cli.find_commands import find_commands
            message = "No command 'conda %(command)s'."
            choices = activate_commands | conda_commands | build_commands | set(find_commands())
            close = get_close_matches(command, choices)
            if close:
                message += "\nDid you mean 'conda %s'?" % close[0]
        super(CommandNotFoundError, self).__init__(message, command=command)


class PathNotFoundError(CondaError, OSError):
    def __init__(self, path):
        message = "%(path)s"
        super(PathNotFoundError, self).__init__(message, path=path)


class DirectoryNotFoundError(CondaError):
    def __init__(self, path):
        message = "%(path)s"
        super(DirectoryNotFoundError, self).__init__(message, path=path)


class EnvironmentLocationNotFound(CondaError):
    def __init__(self, location):
        message = "Not a conda environment: %(location)s"
        super(EnvironmentLocationNotFound, self).__init__(message, location=location)


class EnvironmentNameNotFound(CondaError):
    def __init__(self, environment_name):
        message = dals("""
        Could not find conda environment: %(environment_name)s
        You can list all discoverable environments with `conda info --envs`.
        """)
        super(EnvironmentNameNotFound, self).__init__(message, environment_name=environment_name)


class NoBaseEnvironmentError(CondaError):

    def __init__(self):
        message = dals("""
        This conda installation has no default base environment. Use
        'conda create' to create new environments and 'conda activate' to
        activate environments.
        """)
        super(NoBaseEnvironmentError, self).__init__(message)


class DirectoryNotACondaEnvironmentError(CondaError):

    def __init__(self, target_directory):
        message = dals("""
        The target directory exists, but it is not a conda environment.
        Use 'conda create' to convert the directory to a conda environment.
          target directory: %(target_directory)s
        """)
        super(DirectoryNotACondaEnvironmentError, self).__init__(message,
                                                                 target_directory=target_directory)


class CondaEnvironmentError(CondaError, EnvironmentError):
    def __init__(self, message, *args):
        msg = '%s' % message
        super(CondaEnvironmentError, self).__init__(msg, *args)


class DryRunExit(CondaExitZero):
    def __init__(self):
        msg = 'Dry run. Exiting.'
        super(DryRunExit, self).__init__(msg)


class CondaSystemExit(CondaExitZero, SystemExit):
    def __init__(self, *args):
        msg = ' '.join(text_type(arg) for arg in self.args)
        super(CondaSystemExit, self).__init__(msg)


class PaddingError(CondaError):
    def __init__(self, dist, placeholder, placeholder_length):
        msg = ("Placeholder of length '%d' too short in package %s.\n"
               "The package must be rebuilt with conda-build > 2.0." % (placeholder_length, dist))
        super(PaddingError, self).__init__(msg)


class LinkError(CondaError):
    def __init__(self, message):
        super(LinkError, self).__init__(message)


class CondaOSError(CondaError, OSError):
    def __init__(self, message, **kwargs):
        msg = '%s' % message
        super(CondaOSError, self).__init__(msg, **kwargs)


class ProxyError(CondaError):
    def __init__(self):
        message = dals("""
        Conda cannot proceed due to an error in your proxy configuration.
        Check for typos and other configuration errors in any '.netrc' file in your home directory,
        any environment variables ending in '_PROXY', and any other system-wide proxy
        configuration settings.
        """)
        super(ProxyError, self).__init__(message)


class CondaIOError(CondaError, IOError):
    def __init__(self, message, *args):
        msg = '%s' % message
        super(CondaIOError, self).__init__(msg)


class CondaFileIOError(CondaIOError):
    def __init__(self, filepath, message, *args):
        self.filepath = filepath

        msg = "'%s'. %s" % (filepath, message)
        super(CondaFileIOError, self).__init__(msg, *args)


class CondaKeyError(CondaError, KeyError):
    def __init__(self, key, message, *args):
        self.key = key
        self.msg = "'%s': %s" % (key, message)
        super(CondaKeyError, self).__init__(self.msg, *args)


class ChannelError(CondaError):
    pass


class ChannelNotAllowed(ChannelError):
    def __init__(self, channel):
        from .models.channel import Channel
        from .common.url import maybe_unquote
        channel = Channel(channel)
        channel_name = channel.name
        channel_url = maybe_unquote(channel.base_url)
        message = dals("""
        Channel not included in whitelist:
          channel name: %(channel_name)s
          channel url: %(channel_url)s
        """)
        super(ChannelNotAllowed, self).__init__(message, channel_url=channel_url,
                                                channel_name=channel_name)


class UnavailableInvalidChannel(ChannelError):

    def __init__(self, channel, error_code):
        from .models.channel import Channel
        from .common.url import join_url, maybe_unquote
        channel = Channel(channel)
        channel_name = channel.name
        channel_url = maybe_unquote(channel.base_url)
        message = dals("""
        The channel is not accessible or is invalid.
          channel name: %(channel_name)s
          channel url: %(channel_url)s
          error code: %(error_code)d

        You will need to adjust your conda configuration to proceed.
        Use `conda config --show channels` to view your configuration's current state,
        and use `conda config --show-sources` to view config file locations.
        """)

        if channel.scheme == 'file':
            message += dedent("""
            As of conda 4.3, a valid channel must contain a `noarch/repodata.json` and
            associated `noarch/repodata.json.bz2` file, even if `noarch/repodata.json` is
            empty. Use `conda index %s`, or create `noarch/repodata.json`
            and associated `noarch/repodata.json.bz2`.
            """) % join_url(channel.location, channel.name)

        super(UnavailableInvalidChannel, self).__init__(message, channel_url=channel_url,
                                                        channel_name=channel_name,
                                                        error_code=error_code)


class OperationNotAllowed(CondaError):

    def __init__(self, message):
        super(OperationNotAllowed, self).__init__(message)


class CondaImportError(CondaError, ImportError):
    def __init__(self, message):
        msg = '%s' % message
        super(CondaImportError, self).__init__(msg)


class ParseError(CondaError):
    def __init__(self, message):
        msg = '%s' % message
        super(ParseError, self).__init__(msg)


class CouldntParseError(ParseError):
    def __init__(self, reason):
        self.reason = reason
        super(CouldntParseError, self).__init__(self.args[0])


class ChecksumMismatchError(CondaError):
    def __init__(self, url, target_full_path, checksum_type, expected_checksum, actual_checksum):
        message = dals("""
        Conda detected a mismatch between the expected content and downloaded content
        for url '%(url)s'.
          download saved to: %(target_full_path)s
          expected %(checksum_type)s: %(expected_checksum)s
          actual %(checksum_type)s: %(actual_checksum)s
        """)
        from .common.url import maybe_unquote
        url = maybe_unquote(url)
        super(ChecksumMismatchError, self).__init__(
            message, url=url, target_full_path=target_full_path, checksum_type=checksum_type,
            expected_checksum=expected_checksum, actual_checksum=actual_checksum,
        )


class PackageNotInstalledError(CondaError):

    def __init__(self, prefix, package_name):
        message = dals("""
        Package is not installed in prefix.
          prefix: %(prefix)s
          package name: %(package_name)s
        """)
        super(PackageNotInstalledError, self).__init__(message, prefix=prefix,
                                                       package_name=package_name)


class CondaHTTPError(CondaError):
    def __init__(self, message, url, status_code, reason, elapsed_time, response=None,
                 caused_by=None):
        from .common.url import maybe_unquote
        _message = dals("""
        HTTP %(status_code)s %(reason)s for url <%(url)s>
        Elapsed: %(elapsed_time)s
        """)
        cf_ray = getattr(response, 'headers', {}).get('CF-RAY')
        _message += "CF-RAY: %s\n\n" % cf_ray if cf_ray else "\n"
        message = _message + message

        status_code = status_code or '000'
        reason = reason or 'CONNECTION FAILED'
        elapsed_time = elapsed_time or '-'

        from .auxlib.logz import stringify
        response_details = (stringify(response, content_max_len=1024) or '') if response else ''

        url = maybe_unquote(url)
        if isinstance(elapsed_time, timedelta):
            elapsed_time = text_type(elapsed_time).split(':', 1)[-1]
        if isinstance(reason, string_types):
            reason = reason.upper()
        super(CondaHTTPError, self).__init__(message, url=url, status_code=status_code,
                                             reason=reason, elapsed_time=elapsed_time,
                                             response_details=response_details,
                                             caused_by=caused_by)


class CondaRevisionError(CondaError):
    def __init__(self, message):
        msg = "%s." % message
        super(CondaRevisionError, self).__init__(msg)


class AuthenticationError(CondaError):
    pass


class PackagesNotFoundError(CondaError):

    def __init__(self, packages, channel_urls=()):

        format_list = lambda iterable: '  - ' + '\n  - '.join(text_type(x) for x in iterable)

        if channel_urls:
            message = dals("""
            The following packages are not available from current channels:

            %(packages_formatted)s

            Current channels:

            %(channels_formatted)s

            To search for alternate channels that may provide the conda package you're
            looking for, navigate to

                https://anaconda.org

            and use the search bar at the top of the page.
            """)
            packages_formatted = format_list(packages)
            channels_formatted = format_list(channel_urls)
        else:
            message = dals("""
            The following packages are missing from the target environment:
            %(packages_formatted)s
            """)
            packages_formatted = format_list(packages)
            channels_formatted = ()

        super(PackagesNotFoundError, self).__init__(
            message, packages=packages, packages_formatted=packages_formatted,
            channel_urls=channel_urls, channels_formatted=channels_formatted
        )


class UnsatisfiableError(CondaError):
    """An exception to report unsatisfiable dependencies.

    Args:
        bad_deps: a list of tuples of objects (likely MatchSpecs).
        chains: (optional) if True, the tuples are interpreted as chains
            of dependencies, from top level to bottom. If False, the tuples
            are interpreted as simple lists of conflicting specs.

    Returns:
        Raises an exception with a formatted message detailing the
        unsatisfiable specifications.
    """
    def _format_chain_str(self, bad_deps):
        chains = {}
        for dep in sorted(bad_deps, key=len, reverse=True):
            dep1 = [s.partition(' ') for s in dep[1:]]
            key = (dep[0],) + tuple(v[0] for v in dep1)
            vals = ('',) + tuple(v[2] for v in dep1)
            found = False
            for key2, csets in iteritems(chains):
                if key2[:len(key)] == key:
                    for cset, val in zip(csets, vals):
                        cset.add(val)
                    found = True
            if not found:
                chains[key] = [{val} for val in vals]
        for key, csets in iteritems(chains):
            deps = []
            for name, cset in zip(key, csets):
                if '' not in cset:
                    pass
                elif len(cset) == 1:
                    cset.clear()
                else:
                    cset.remove('')
                    cset.add('*')
                if name[0] == '@':
                    name = 'feature:' + name[1:]
                deps.append('%s %s' % (name, '|'.join(sorted(cset))) if cset else name)
            chains[key] = ' -> '.join(deps)
        bad_deps = [chains[key] for key in sorted(iterkeys(chains))]
        return bad_deps

    def __init__(self, bad_deps, chains=True, strict=False):
        from .models.match_spec import MatchSpec

        messages = {'python': dals('''

The following specifications were found
to be incompatible with the existing python installation in your environment:

Specifications:\n{specs}

Your python: {ref}

If python is on the left-most side of the chain, that's the version you've asked for.
When python appears to the right, that indicates that the thing on the left is somehow
not available for the python version you are constrained to. Note that conda will not
change your python version to a different minor version unless you explicitly specify
that.

        '''),
                    'request_conflict_with_history': dals('''

The following specifications were found to be incompatible with a past
explicit spec that is not an explicit spec in this operation ({ref}):\n{specs}

                    '''),
                    'direct': dals('''

The following specifications were found to be incompatible with each other:
                    '''),
                    'virtual_package': dals('''

The following specifications were found to be incompatible with your system:\n{specs}

Your installed version is: {ref}
''')}

        msg = ""
        self.unsatisfiable = []
        if len(bad_deps) == 0:
            msg += '''
Did not find conflicting dependencies. If you would like to know which
packages conflict ensure that you have enabled unsatisfiable hints.

conda config --set unsatisfiable_hints True
            '''
        else:
            for class_name, dep_class in bad_deps.items():
                if dep_class:
                    _chains = []
                    if class_name == "direct":
                        msg += messages["direct"]
                        last_dep_entry = set(d[0][-1].name for d in dep_class)
                        dep_constraint_map = {}
                        for dep in dep_class:
                            if dep[0][-1].name in last_dep_entry:
                                if not dep_constraint_map.get(dep[0][-1].name):
                                    dep_constraint_map[dep[0][-1].name] = []
                                dep_constraint_map[dep[0][-1].name].append(dep[0])
                        msg += "\nOutput in format: Requested package -> Available versions"
                        for dep, chain in dep_constraint_map.items():
                            if len(chain) > 1:
                                msg += "\n\nPackage %s conflicts for:\n" % dep
                                msg += "\n".join([" -> ".join([str(i) for i in c]) for c in chain])
                                self.unsatisfiable += [tuple(entries) for entries in chain]
                    else:
                        for dep_chain, installed_blocker in dep_class:
                            # Remove any target values from the MatchSpecs, convert to strings
                            dep_chain = [str(MatchSpec(dep, target=None)) for dep in dep_chain]
                            _chains.append(dep_chain)

                        if _chains:
                            _chains = self._format_chain_str(_chains)
                        else:
                            _chains = [', '.join(c) for c in _chains]
                        msg += messages[class_name].format(specs=dashlist(_chains),
                                                           ref=installed_blocker)
        if strict:
            msg += ('\nNote that strict channel priority may have removed '
                    'packages required for satisfiability.')

        super(UnsatisfiableError, self).__init__(msg)


class InstallError(CondaError):
    def __init__(self, message):
        msg = '%s' % message
        super(InstallError, self).__init__(msg)


class RemoveError(CondaError):
    def __init__(self, message):
        msg = '%s' % message
        super(RemoveError, self).__init__(msg)


class DisallowedPackageError(CondaError):
    def __init__(self, package_ref, **kwargs):
        from .models.records import PackageRecord
        package_ref = PackageRecord.from_objects(package_ref)
        message = ("The package '%(dist_str)s' is disallowed by configuration.\n"
                   "See 'conda config --show disallowed_packages'.")
        super(DisallowedPackageError, self).__init__(message, package_ref=package_ref,
                                                     dist_str=package_ref.dist_str(), **kwargs)

class SpecsConfigurationConflictError(CondaError):

    def __init__(self, requested_specs, pinned_specs, prefix):
        message = dals("""
        Requested specs conflict with configured specs.
          requested specs: {requested_specs_formatted}
          pinned specs: {pinned_specs_formatted}
        Use 'conda config --show-sources' to look for 'pinned_specs' and 'track_features'
        configuration parameters.  Pinned specs may also be defined in the file
        {pinned_specs_path}.
        """).format(
            requested_specs_formatted=dashlist(requested_specs, 4),
            pinned_specs_formatted=dashlist(pinned_specs, 4),
            pinned_specs_path=join(prefix, 'conda-meta', 'pinned'),
        )
        super(SpecsConfigurationConflictError, self).__init__(
            message, requested_specs=requested_specs, pinned_specs=pinned_specs, prefix=prefix,
        )

class CondaIndexError(CondaError, IndexError):
    def __init__(self, message):
        msg = '%s' % message
        super(CondaIndexError, self).__init__(msg)


class CondaValueError(CondaError, ValueError):

    def __init__(self, message, *args, **kwargs):
        super(CondaValueError, self).__init__(message, *args, **kwargs)


class CondaTypeError(CondaError, TypeError):
    def __init__(self, expected_type, received_type, optional_message):
        msg = "Expected type '%s' and got type '%s'. %s"
        super(CondaTypeError, self).__init__(msg)


class CyclicalDependencyError(CondaError, ValueError):
    def __init__(self, packages_with_cycles, **kwargs):
        from .models.records import PackageRecord
        packages_with_cycles = tuple(PackageRecord.from_objects(p) for p in packages_with_cycles)
        message = "Cyclic dependencies exist among these items: %s" % dashlist(
            p.dist_str() for p in packages_with_cycles
        )
        super(CyclicalDependencyError, self).__init__(
            message, packages_with_cycles=packages_with_cycles, **kwargs
        )


class CorruptedEnvironmentError(CondaError):
    def __init__(self, environment_location, corrupted_file, **kwargs):
        message = dals("""
        The target environment has been corrupted. Corrupted environments most commonly
        occur when the conda process is force-terminated while in an unlink-link
        transaction.
          environment location: %(environment_location)s
          corrupted file: %(corrupted_file)s
        """)
        super(CorruptedEnvironmentError, self).__init__(
            message,
            environment_location=environment_location,
            corrupted_file=corrupted_file,
            **kwargs
        )


class CondaHistoryError(CondaError):
    def __init__(self, message):
        msg = '%s' % message
        super(CondaHistoryError, self).__init__(msg)


class CondaUpgradeError(CondaError):
    def __init__(self, message):
        msg = "%s" % message
        super(CondaUpgradeError, self).__init__(msg)


class CaseInsensitiveFileSystemError(CondaError):
    def __init__(self, package_location, extract_location, **kwargs):
        message = dals("""
        Cannot extract package to a case-insensitive file system.
          package location: %(package_location)s
          extract location: %(extract_location)s
        """)
        super(CaseInsensitiveFileSystemError, self).__init__(
            message,
            package_location=package_location,
            extract_location=extract_location,
            **kwargs
        )


class CondaVerificationError(CondaError):
    def __init__(self, message):
        super(CondaVerificationError, self).__init__(message)


class SafetyError(CondaError):
    def __init__(self, message):
        super(SafetyError, self).__init__(message)


class CondaMemoryError(CondaError, MemoryError):
    def __init__(self, caused_by, **kwargs):
        message = "The conda process ran out of memory. Increase system memory and/or try again."
        super(CondaMemoryError, self).__init__(message, caused_by=caused_by, **kwargs)


class NotWritableError(CondaError, OSError):

    def __init__(self, path, errno, **kwargs):
        kwargs.update({
            'path': path,
            'errno': errno,
        })
        if on_win:
            message = dals("""
            The current user does not have write permissions to a required path.
              path: %(path)s
            """)
        else:
            message = dals("""
            The current user does not have write permissions to a required path.
              path: %(path)s
              uid: %(uid)s
              gid: %(gid)s

            If you feel that permissions on this path are set incorrectly, you can manually
            change them by executing

              $ sudo chown %(uid)s:%(gid)s %(path)s

            In general, it's not advisable to use 'sudo conda'.
            """)
            kwargs.update({
                'uid': os.geteuid(),
                'gid': os.getegid(),
            })
        super(NotWritableError, self).__init__(message, **kwargs)
        self.errno = errno


class NoWritableEnvsDirError(CondaError):

    def __init__(self, envs_dirs, **kwargs):
        message = "No writeable envs directories configured.%s" % dashlist(envs_dirs)
        super(NoWritableEnvsDirError, self).__init__(message, envs_dirs=envs_dirs, **kwargs)


class NoWritablePkgsDirError(CondaError):

    def __init__(self, pkgs_dirs, **kwargs):
        message = "No writeable pkgs directories configured.%s" % dashlist(pkgs_dirs)
        super(NoWritablePkgsDirError, self).__init__(message, pkgs_dirs=pkgs_dirs, **kwargs)


class EnvironmentNotWritableError(CondaError):

    def __init__(self, environment_location, **kwargs):
        kwargs.update({
            'environment_location': environment_location,
        })
        if on_win:
            message = dals("""
            The current user does not have write permissions to the target environment.
              environment location: %(environment_location)s
            """)
        else:
            message = dals("""
            The current user does not have write permissions to the target environment.
              environment location: %(environment_location)s
              uid: %(uid)s
              gid: %(gid)s
            """)
            kwargs.update({
                'uid': os.geteuid(),
                'gid': os.getegid(),
            })
        super(EnvironmentNotWritableError, self).__init__(message, **kwargs)


class CondaDependencyError(CondaError):
    def __init__(self, message):
        super(CondaDependencyError, self).__init__(message)


class BinaryPrefixReplacementError(CondaError):
    def __init__(self, path, placeholder, new_prefix, original_data_length, new_data_length):
        message = dals("""
        Refusing to replace mismatched data length in binary file.
          path: %(path)s
          placeholder: %(placeholder)s
          new prefix: %(new_prefix)s
          original data Length: %(original_data_length)d
          new data length: %(new_data_length)d
        """)
        kwargs = {
            'path': path,
            'placeholder': placeholder,
            'new_prefix': new_prefix,
            'original_data_length': original_data_length,
            'new_data_length': new_data_length,
        }
        super(BinaryPrefixReplacementError, self).__init__(message, **kwargs)


class InvalidSpec(CondaError, ValueError):

    def __init__(self, message, **kwargs):
        super(InvalidSpec, self).__init__(message, **kwargs)


class InvalidVersionSpec(InvalidSpec):
    def __init__(self, invalid_spec, details):
        message = "Invalid version '%(invalid_spec)s': %(details)s"
        super(InvalidVersionSpec, self).__init__(message, invalid_spec=invalid_spec,
                                                 details=details)


class InvalidMatchSpec(InvalidSpec):
    def __init__(self, invalid_spec, details):
        message = "Invalid spec '%(invalid_spec)s': %(details)s"
        super(InvalidMatchSpec, self).__init__(message, invalid_spec=invalid_spec,
                                               details=details)


class EncodingError(CondaError):

    def __init__(self, caused_by, **kwargs):
        message = dals("""
        A unicode encoding or decoding error has occurred.
        Python 2 is the interpreter under which conda is running in your base environment.
        Replacing your base environment with one having Python 3 may help resolve this issue.
        If you still have a need for Python 2 environments, consider using 'conda create'
        and 'conda activate'.  For example:

            $ conda create -n py2 python=2
            $ conda activate py2

        Error details: %r

        """) % caused_by
        super(EncodingError, self).__init__(message, caused_by=caused_by, **kwargs)


class NoSpaceLeftError(CondaError):

    def __init__(self, caused_by, **kwargs):
        message = "No space left on devices."
        super(NoSpaceLeftError, self).__init__(message, caused_by=caused_by, **kwargs)


def maybe_raise(error, context):
    if isinstance(error, CondaMultiError):
        groups = groupby(lambda e: isinstance(e, ClobberError), error.errors)
        clobber_errors = groups.get(True, ())
        groups = groupby(lambda e: isinstance(e, SafetyError), groups.get(False, ()))
        safety_errors = groups.get(True, ())
        other_errors = groups.get(False, ())

        if ((safety_errors and context.safety_checks == SafetyChecks.enabled)
                or (clobber_errors and context.path_conflict == PathConflict.prevent
                    and not context.clobber)
                or other_errors):
            raise error
        elif ((safety_errors and context.safety_checks == SafetyChecks.warn)
              or (clobber_errors and context.path_conflict == PathConflict.warn
                  and not context.clobber)):
            print_conda_exception(error)

    elif isinstance(error, ClobberError):
        if context.path_conflict == PathConflict.prevent and not context.clobber:
            raise error
        elif context.path_conflict == PathConflict.warn and not context.clobber:
            print_conda_exception(error)

    elif isinstance(error, SafetyError):
        if context.safety_checks == SafetyChecks.enabled:
            raise error
        elif context.safety_checks == SafetyChecks.warn:
            print_conda_exception(error)

    else:
        raise error


def print_conda_exception(exc_val, exc_tb=None):
    from .base.context import context
    rc = getattr(exc_val, 'return_code', None)
    if (context.debug
            or context.verbosity > 2
            or (not isinstance(exc_val, DryRunExit) and context.verbosity > 0)):
        print(_format_exc(exc_val, exc_tb), file=sys.stderr)
    elif context.json:
        if isinstance(exc_val, DryRunExit):
            return
        logger = getLogger('conda.stdout' if rc else 'conda.stderr')
        exc_json = json.dumps(exc_val.dump_map(), indent=2, sort_keys=True, cls=EntityEncoder)
        logger.info("%s\n" % exc_json)
    else:
        stderrlog = getLogger('conda.stderr')
        stderrlog.error("\n%r\n", exc_val)
        # An alternative which would allow us not to reload sys with newly setdefaultencoding()
        # is to not use `%r`, e.g.:
        # Still, not being able to use `%r` seems too great a price to pay.
        # stderrlog.error("\n" + exc_val.__repr__() + \n")


def _format_exc(exc_val=None, exc_tb=None):
    if exc_val is None:
        exc_type, exc_val, exc_tb = sys.exc_info()
    else:
        exc_type = type(exc_val)
    if exc_tb:
        formatted_exception = format_exception(exc_type, exc_val, exc_tb)
    else:
        formatted_exception = format_exception_only(exc_type, exc_val)
    return ''.join(formatted_exception)


class ExceptionHandler(object):

    def __call__(self, func, *args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:  # lgtm [py/catch-base-exception]
            _, exc_val, exc_tb = sys.exc_info()
            return self.handle_exception(exc_val, exc_tb)

    def write_out(self, content_str):
        from .base.context import context
        if True:
            logger = getLogger("conda.%s" % ("stdout" if context.json else "stderr"))
            logger.info(content_str)
        else:
            stream = sys.stdout if context.json else sys.stderr
            stream.write(content_str)

    @property
    def http_timeout(self):
        from .base.context import context
        return context.remote_connect_timeout_secs, context.remote_read_timeout_secs

    @property
    def user_agent(self):
        from .base.context import context
        return context.user_agent

    @property
    def error_upload_url(self):
        from .base.context import context
        return context.error_upload_url

    def handle_exception(self, exc_val, exc_tb):
        if isinstance(exc_val, CondaError):
            if exc_val.reportable:
                return self.handle_reportable_application_exception(exc_val, exc_tb)
            else:
                return self.handle_application_exception(exc_val, exc_tb)
        if isinstance(exc_val, UnicodeError) and PY2:
            return self.handle_application_exception(EncodingError(exc_val), exc_tb)
        if isinstance(exc_val, EnvironmentError):
            if getattr(exc_val, 'errno', None) == ENOSPC:
                return self.handle_application_exception(NoSpaceLeftError(exc_val), exc_tb)
        if isinstance(exc_val, MemoryError):
            return self.handle_application_exception(CondaMemoryError(exc_val), exc_tb)
        if isinstance(exc_val, KeyboardInterrupt):
            self._print_conda_exception(CondaError("KeyboardInterrupt"), _format_exc())
            return 1
        if isinstance(exc_val, SystemExit):
            return exc_val.code
        return self.handle_unexpected_exception(exc_val, exc_tb)

    def handle_application_exception(self, exc_val, exc_tb):
        self._print_conda_exception(exc_val, exc_tb)
        return exc_val.return_code

    def _print_conda_exception(self, exc_val, exc_tb):
        print_conda_exception(exc_val, exc_tb)

    def handle_unexpected_exception(self, exc_val, exc_tb):
        error_report = self.get_error_report(exc_val, exc_tb)
        self.print_unexpected_error_report(error_report)
        ask_for_upload, do_upload = self._calculate_ask_do_upload()
        do_upload, ask_response = self.ask_for_upload() if ask_for_upload else (do_upload, None)
        if do_upload:
            self._execute_upload(error_report)
        self.print_upload_confirm(do_upload, ask_for_upload, ask_response)
        rc = getattr(exc_val, 'return_code', None)
        return rc if rc is not None else 1

    def handle_reportable_application_exception(self, exc_val, exc_tb):
        error_report = self.get_error_report(exc_val, exc_tb)
        from .base.context import context
        if context.json:
            error_report.update(exc_val.dump_map())
        self.print_expected_error_report(error_report)
        ask_for_upload, do_upload = self._calculate_ask_do_upload()
        do_upload, ask_response = self.ask_for_upload() if ask_for_upload else (do_upload, None)
        if do_upload:
            self._execute_upload(error_report)
        self.print_upload_confirm(do_upload, ask_for_upload, ask_response)
        return exc_val.return_code

    def get_error_report(self, exc_val, exc_tb):
        command = ' '.join(ensure_text_type(s) for s in sys.argv)
        info_dict = {}
        if ' info' not in command:
            # get info_dict, but if we get an exception here too, record it without trampling
            # the original exception
            try:
                from .cli.main_info import get_info_dict
                info_dict = get_info_dict()
            except Exception as info_e:
                info_traceback = _format_exc()
                info_dict = {
                    'error': repr(info_e),
                    'exception_name': info_e.__class__.__name__,
                    'exception_type': text_type(exc_val.__class__),
                    'traceback': info_traceback,
                }

        error_report = {
            'error': repr(exc_val),
            'exception_name': exc_val.__class__.__name__,
            'exception_type': text_type(exc_val.__class__),
            'command': command,
            'traceback': _format_exc(exc_val, exc_tb),
            'conda_info': info_dict,
        }

        if isinstance(exc_val, CondaError):
            error_report['conda_error_components'] = exc_val.dump_map()

        return error_report

    def print_unexpected_error_report(self, error_report):
        from .base.context import context
        if context.json:
            from .cli.common import stdout_json
            stdout_json(error_report)
        else:
            message_builder = []
            message_builder.append('')
            message_builder.append('# >>>>>>>>>>>>>>>>>>>>>> ERROR REPORT <<<<<<<<<<<<<<<<<<<<<<')
            message_builder.append('')
            message_builder.extend('    ' + line
                                   for line in error_report['traceback'].splitlines())
            message_builder.append('')
            message_builder.append('`$ %s`' % error_report['command'])
            message_builder.append('')
            if error_report['conda_info']:
                from .cli.main_info import get_env_vars_str, get_main_info_str
                try:
                    # TODO: Sanitize env vars to remove secrets (e.g credentials for PROXY)
                    message_builder.append(get_env_vars_str(error_report['conda_info']))
                    message_builder.append(get_main_info_str(error_report['conda_info']))
                except Exception as e:
                    log.warn("%r", e, exc_info=True)
                    message_builder.append('conda info could not be constructed.')
                    message_builder.append('%r' % e)
            message_builder.append('')
            message_builder.append(
                "An unexpected error has occurred. Conda has prepared the above report."
            )
            message_builder.append('')
            self.write_out('\n'.join(message_builder))

    def print_expected_error_report(self, error_report):
        from .base.context import context
        if context.json:
            from .cli.common import stdout_json
            stdout_json(error_report)
        else:
            message_builder = []
            message_builder.append('')
            message_builder.append('# >>>>>>>>>>>>>>>>>>>>>> ERROR REPORT <<<<<<<<<<<<<<<<<<<<<<')
            message_builder.append('')
            message_builder.append('`$ %s`' % error_report['command'])
            message_builder.append('')
            if error_report['conda_info']:
                from .cli.main_info import get_env_vars_str, get_main_info_str
                try:
                    # TODO: Sanitize env vars to remove secrets (e.g credentials for PROXY)
                    message_builder.append(get_env_vars_str(error_report['conda_info']))
                    message_builder.append(get_main_info_str(error_report['conda_info']))
                except Exception as e:
                    log.warn("%r", e, exc_info=True)
                    message_builder.append('conda info could not be constructed.')
                    message_builder.append('%r' % e)
            message_builder.append('')
            message_builder.append('V V V V V V V V V V V V V V V V V V V V V V V V V V V V V V V')
            message_builder.append('')

            message_builder.extend(error_report['error'].splitlines())
            message_builder.append('')

            message_builder.append(
                "A reportable application error has occurred. Conda has prepared the above report."
            )
            message_builder.append('')
            self.write_out('\n'.join(message_builder))

    def _calculate_ask_do_upload(self):
        from .base.context import context

        try:
            isatty = os.isatty(0) or on_win
        except Exception as e:
            log.debug('%r', e)
            # given how the rest of this function is constructed, better to assume True here
            isatty = True

        if context.report_errors is False:
            ask_for_upload = False
            do_upload = False
        elif context.report_errors is True or context.always_yes:
            ask_for_upload = False
            do_upload = True
        elif context.json or context.quiet:
            ask_for_upload = False
            do_upload = not context.offline and context.always_yes
        elif not isatty:
            ask_for_upload = False
            do_upload = not context.offline and context.always_yes
        else:
            ask_for_upload = True
            do_upload = False

        return ask_for_upload, do_upload

    def ask_for_upload(self):
        self.write_out(dals("""
        If submitted, this report will be used by core maintainers to improve
        future releases of conda.
        Would you like conda to send this report to the core maintainers?
        """))
        ask_response = None
        try:
            ask_response = timeout(40, partial(input, "[y/N]: "))
            do_upload = ask_response and boolify(ask_response)
        except Exception as e:  # pragma: no cover
            log.debug('%r', e)
            do_upload = False
        return do_upload, ask_response

    def _execute_upload(self, error_report):
        headers = {
            'User-Agent': self.user_agent,
        }
        _timeout = self.http_timeout
        username = getpass.getuser()
        error_report['is_ascii'] = True if all(ord(c) < 128 for c in username) else False
        error_report['has_spaces'] = True if " " in str(username) else False
        data = json.dumps(error_report, sort_keys=True, cls=EntityEncoder) + '\n'
        data = data.replace(str(username), "USERNAME_REMOVED")
        response = None
        try:
            # requests does not follow HTTP standards for redirects of non-GET methods
            # That is, when following a 301 or 302, it turns a POST into a GET.
            # And no way to disable.  WTF
            import requests
            redirect_counter = 0
            url = self.error_upload_url
            response = requests.post(url, headers=headers, timeout=_timeout, data=data,
                                     allow_redirects=False)
            response.raise_for_status()
            while response.status_code in (301, 302) and response.headers.get('Location'):
                url = response.headers['Location']
                response = requests.post(url, headers=headers, timeout=_timeout, data=data,
                                         allow_redirects=False)
                response.raise_for_status()
                redirect_counter += 1
                if redirect_counter > 15:
                    raise CondaError("Redirect limit exceeded")
            log.debug("upload response status: %s", response and response.status_code)
        except Exception as e:  # pragma: no cover
            log.info('%r', e)
        try:
            if response and response.ok:
                self.write_out("Upload successful.")
            else:
                self.write_out("Upload did not complete.")
                if response and response.status_code:
                    self.write_out(" HTTP %s" % response.status_code)
        except Exception as e:
            log.debug("%r" % e)

    def print_upload_confirm(self, do_upload, ask_for_upload, ask_response):
        if ask_response and do_upload:
            self.write_out(
                "\n"
                "Thank you for helping to improve conda.\n"
                "Opt-in to always sending reports (and not see this message again)\n"
                "by running\n"
                "\n"
                "    $ conda config --set report_errors true\n"
                "\n"
            )
        elif ask_response is None and ask_for_upload:
            # means timeout was reached for `input`
            self.write_out(  # lgtm [py/unreachable-statement]
                '\nTimeout reached. No report sent.\n'
            )
        elif ask_for_upload:
            self.write_out(
                "\n"
                "No report sent. To permanently opt-out, use\n"
                "\n"
                "    $ conda config --set report_errors false\n"
                "\n"
            )


def conda_exception_handler(func, *args, **kwargs):
    exception_handler = ExceptionHandler()
    return_value = exception_handler(func, *args, **kwargs)
    return return_value
