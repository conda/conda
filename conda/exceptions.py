# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import timedelta
from errno import ENOSPC
import json
from logging import getLogger
import os
import sys
from traceback import format_exception, format_exception_only

from . import CondaError, CondaExitZero, CondaMultiError, text_type
from ._vendor.auxlib.entity import EntityEncoder
from ._vendor.auxlib.ish import dals
from ._vendor.auxlib.type_coercion import boolify
from .base.constants import PathConflict, SafetyChecks
from .common.compat import ensure_text_type, input, iteritems, iterkeys, on_win, string_types, PY2
from .common.io import timeout
from .common.signals import get_signal_name
from .common.url import maybe_unquote

try:
    from cytoolz.itertoolz import groupby
except ImportError:  # pragma: no cover
    from ._vendor.toolz.itertoolz import groupby  # NOQA

log = getLogger(__name__)


# TODO: for conda-build compatibility only
# remove in conda 4.4
class ResolvePackageNotFound(CondaError):
    def __init__(self, bad_deps):
        # bad_deps is a list of lists
        self.bad_deps = tuple(dep for deps in bad_deps for dep in deps if dep)
        message = '\n' + '\n'.join(('  - %s' % dep) for dep in self.bad_deps)
        super(ResolvePackageNotFound, self).__init__(message)
NoPackagesFound = NoPackagesFoundError = ResolvePackageNotFound  # NOQA


class LockError(CondaError):
    def __init__(self, message):
        msg = "%s" % message
        super(LockError, self).__init__(msg)


class ArgumentError(CondaError):
    def __init__(self, message, **kwargs):
        super(ArgumentError, self).__init__(message, **kwargs)


class CommandArgumentError(ArgumentError):
    def __init__(self, message, **kwargs):
        command = ' '.join(ensure_text_type(s) for s in sys.argv)
        super(CommandArgumentError, self).__init__(message, command=command, **kwargs)


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
        return '%s: %s\n' % (clz_name, text_type(self))


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
        # TODO: Point users to a page at conda-docs, which explains this context in more detail
        if command in activate_commands:
            from .base.context import context
            builder = ["Your shell has not been properly configured to use 'conda %(command)s'."]
            builder.append(dals("""
            If your shell is Bash or a Bourne variant, enable conda for the current user with

                $ echo ". %(root_prefix)s/etc/profile.d/conda.sh" >> ~/%(config_file)s

            or, for all users, enable conda with

                $ sudo ln -s %(root_prefix)s/etc/profile.d/conda.sh /etc/profile.d/conda.sh

            The options above will permanently enable the 'conda' command, but they do NOT
            put conda's base (root) environment on PATH.  To do so, run

                $ conda activate

            in your terminal, or to put the base environment on PATH permanently, run

                $ echo "conda activate" >> ~/%(config_file)s

            Previous to conda 4.4, the recommended way to activate conda was to modify PATH in
            your ~/%(config_file)s file.  You should manually remove the line that looks like

                export PATH="%(root_prefix)s/bin:$PATH"

            ^^^ The above line should NO LONGER be in your ~/%(config_file)s file! ^^^
            """) % {
                'root_prefix': context.root_prefix,
                'macos_fix': " ''" if sys.platform == 'darwin' else "",
                'config_file': '.bash_profile' if sys.platform == 'darwin' else '.bashrc',
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
        from .base.context import context
        from .cli.main import init_loggers
        init_loggers(context)
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


class CondaEnvironmentError(CondaError, EnvironmentError):
    def __init__(self, message, *args):
        msg = '%s' % message
        super(CondaEnvironmentError, self).__init__(msg, *args)


class DryRunExit(CondaExitZero):
    def __init__(self):
        msg = 'Dry run exiting'
        super(DryRunExit, self).__init__(msg)


class CondaSystemExit(CondaExitZero, SystemExit):
    def __init__(self, *args):
        msg = ' '.join(text_type(arg) for arg in self.args)
        super(CondaSystemExit, self).__init__(msg)


class SubprocessExit(CondaExitZero):
    def __init__(self, *args, **kwargs):
        super(SubprocessExit, self).__init__(*args, **kwargs)


class PaddingError(CondaError):
    def __init__(self, dist, placeholder, placeholder_length):
        msg = ("Placeholder of length '%d' too short in package %s.\n"
               "The package must be rebuilt with conda-build > 2.0." % (placeholder_length, dist))
        super(PaddingError, self).__init__(msg)


class LinkError(CondaError):
    def __init__(self, message):
        super(LinkError, self).__init__(message)


class CondaOSError(CondaError, OSError):
    def __init__(self, message):
        msg = '%s' % message
        super(CondaOSError, self).__init__(msg)


class ProxyError(CondaError):
    def __init__(self, message):
        msg = '%s' % message
        super(ProxyError, self).__init__(msg)


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
    def __init__(self, message, *args):
        msg = '%s' % message
        super(ChannelError, self).__init__(msg)


class ChannelNotAllowed(ChannelError):
    def __init__(self, message, *args):
        msg = '%s' % message
        super(ChannelNotAllowed, self).__init__(msg, *args)


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


class MD5MismatchError(CondaError):
    def __init__(self, url, target_full_path, expected_md5sum, actual_md5sum):
        message = dals("""
        Conda detected a mismatch between the expected content and downloaded content
        for url '%(url)s'.
          download saved to: %(target_full_path)s
          expected md5 sum: %(expected_md5sum)s
          actual md5 sum: %(actual_md5sum)s
        """)
        url = maybe_unquote(url)
        super(MD5MismatchError, self).__init__(message, url=url, target_full_path=target_full_path,
                                               expected_md5sum=expected_md5sum,
                                               actual_md5sum=actual_md5sum)


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

        from ._vendor.auxlib.logz import stringify
        response_details = (stringify(response) or '') if response else ''

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

    def __init__(self, bad_deps, chains=True):
        from .models.match_spec import MatchSpec
        from .resolve import dashlist

        # Remove any target values from the MatchSpecs, convert to strings
        bad_deps = [list(map(lambda x: str(MatchSpec(x, target=None)), dep)) for dep in bad_deps]
        if chains:
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
            msg = '''The following specifications were found to be in conflict:%s
Use "conda info <package>" to see the dependencies for each package.'''
        else:
            bad_deps = [sorted(dep) for dep in bad_deps]
            bad_deps = [', '.join(dep) for dep in sorted(bad_deps)]
            msg = '''The following specifications were found to be incompatible with the
others, or with the existing package set:%s
Use "conda info <package>" to see the dependencies for each package.'''
        msg = msg % dashlist(bad_deps)
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
        from .models.records import PackageRef
        package_ref = PackageRef.from_objects(package_ref)
        message = ("The package '%(dist_str)s' is disallowed by configuration.\n"
                   "See 'conda config --show disallowed_packages'.")
        super(DisallowedPackageError, self).__init__(message, package_ref=package_ref,
                                                     dist_str=package_ref.dist_str(), **kwargs)


class CondaIndexError(CondaError, IndexError):
    def __init__(self, message):
        msg = '%s' % message
        super(CondaIndexError, self).__init__(msg)


class CondaValueError(CondaError, ValueError):
    def __init__(self, message, *args):
        msg = '%s' % message
        super(CondaValueError, self).__init__(msg)


class CondaTypeError(CondaError, TypeError):
    def __init__(self, expected_type, received_type, optional_message):
        msg = "Expected type '%s' and got type '%s'. %s"
        super(CondaTypeError, self).__init__(msg)


class CyclicalDependencyError(CondaError, ValueError):
    def __init__(self, packages_with_cycles, **kwargs):
        from .resolve import dashlist
        from .models.records import PackageRef
        packages_with_cycles = tuple(PackageRef.from_objects(p) for p in packages_with_cycles)
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
            import os
            kwargs.update({
                'uid': os.geteuid(),
                'gid': os.getegid(),
            })
        super(NotWritableError, self).__init__(message, **kwargs)


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


class InvalidVersionSpecError(CondaError):
    def __init__(self, invalid_spec):
        message = "Invalid version spec: %(invalid_spec)s"
        super(InvalidVersionSpecError, self).__init__(message, invalid_spec=invalid_spec)


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
    if context.debug or context.verbosity > 0:
        sys.stderr.write(_format_exc(exc_val, exc_tb))
        sys.stderr.write('\n')
    elif context.json:
        import json
        stdoutlog = getLogger('conda.stdout')
        exc_json = json.dumps(exc_val.dump_map(), indent=2, sort_keys=True, cls=EntityEncoder)
        stdoutlog.info("%s\n" % exc_json)
    else:
        stderrlog = getLogger('conda.stderr')
        stderrlog.info("\n%r\n", exc_val)


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
        except:
            _, exc_val, exc_tb = sys.exc_info()
            return self.handle_exception(exc_val, exc_tb)

    @property
    def out_stream(self):
        from .base.context import context
        return sys.stdout if context.json else sys.stderr

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
        return_code = getattr(exc_val, 'return_code', None)
        if return_code == 0:
            return 0
        if isinstance(exc_val, CondaHTTPError):
            return self.handle_reportable_application_exception(exc_val, exc_tb)
        if isinstance(exc_val, CondaError):
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
        rc = getattr(exc_val, 'return_code', None)
        return rc if rc is not None else 1

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
        rc = getattr(exc_val, 'return_code', None)
        return rc if rc is not None else 1

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
            self.out_stream.write('\n'.join(message_builder))

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
            self.out_stream.write('\n'.join(message_builder))

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
        message_builder = [
            "If submitted, this report will be used by core maintainers to improve",
            "future releases of conda.",
            "Would you like conda to send this report to the core maintainers?",
        ]
        message_builder.append(
            "[y/N]: "
        )
        self.out_stream.write('\n'.join(message_builder))
        ask_response = None
        try:
            ask_response = timeout(40, input)
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
        data = json.dumps(error_report, sort_keys=True, cls=EntityEncoder) + '\n'
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
                self.out_stream.write("Upload successful.\n")
            else:
                self.out_stream.write("Upload did not complete.")
                if response and response.status_code:
                    self.out_stream.write(" HTTP %s" % response.status_code)
                    self.out_stream.write("\n")
        except Exception as e:
            log.debug("%r" % e)

    def print_upload_confirm(self, do_upload, ask_for_upload, ask_response):
        if ask_response and do_upload:
            self.out_stream.write(
                "\n"
                "Thank you for helping to improve conda.\n"
                "Opt-in to always sending reports (and not see this message again)\n"
                "by running\n"
                "\n"
                "    $ conda config --set report_errors true\n"
                "\n"
            )
        elif ask_for_upload:
            self.out_stream.write(
                "\n"
                "No report sent. To permanently opt-out, use\n"
                "\n"
                "    $ conda config --set report_errors false\n"
                "\n"
            )
        elif ask_response is None and ask_for_upload:
            # means timeout was reached for `input`
            self.out_stream.write(  # lgtm [py/unreachable-statement]
                '\nTimeout reached. No report sent.\n'
            )


def conda_exception_handler(func, *args, **kwargs):
    exception_handler = ExceptionHandler()
    return_value = exception_handler(func, *args, **kwargs)
    if isinstance(return_value, int):
        return return_value
