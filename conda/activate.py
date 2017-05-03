# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from glob import glob
import os
from os.path import abspath, basename, dirname, expanduser, expandvars, isdir, join, normpath
import re
import sys
from tempfile import NamedTemporaryFile

try:
    from cytoolz.itertoolz import concatv, drop
except ImportError:  # pragma: no cover
    from ._vendor.toolz.itertoolz import concatv, drop  # NOQA

class Activator(object):
    # Activate and deactivate have three tasks
    #   1. Set and unset environment variables
    #   2. Execute/source activate.d/deactivate.d scripts
    #   3. Update the command prompt
    #
    # Shells should also use 'reactivate' following conda's install, update, and
    #   remove/uninstall commands.
    #
    # All core logic is in build_activate() or build_deactivate(), and is independent of
    # shell type.  Each returns a map containing the keys:
    #   set_vars
    #   unset_var
    #   activate_scripts
    #   deactivate_scripts
    #
    # The value of the CONDA_PROMPT_MODIFIER environment variable holds conda's contribution
    #   to the command prompt.
    #
    # To implement support for a new shell, ideally one would only need to add shell-specific
    # information to the __init__ method of this class.

    def __init__(self, shell, arguments=None):
        from .base.context import context
        self.context = context
        self.shell = shell
        self._raw_arguments = arguments

        if shell == 'posix':
            self.pathsep_join = ':'.join
            self.path_conversion = native_path_to_unix
            self.script_extension = '.sh'
            self.tempfile_extension = None  # write instructions to stdout rather than a temp file
            self.shift_args = 0

            self.unset_var_tmpl = 'unset %s'
            self.set_var_tmpl = 'export %s="%s"'
            self.run_script_tmpl = '. "%s"'

        elif shell == 'csh':
            self.pathsep_join = ':'.join
            self.path_conversion = native_path_to_unix
            self.script_extension = '.csh'
            self.tempfile_extension = None  # write instructions to stdout rather than a temp file
            self.shift_args = 0

            self.unset_var_tmpl = 'unset %s'
            self.set_var_tmpl = 'setenv %s "%s"'
            self.run_script_tmpl = 'source "%s"'

        elif shell == 'xonsh':
            self.pathsep_join = ':'.join
            self.path_conversion = native_path_to_unix
            self.script_extension = '.xsh'
            self.tempfile_extension = '.xsh'
            self.shift_args = 0

            self.unset_var_tmpl = 'del $%s'
            self.set_var_tmpl = '$%s = "%s"'
            self.run_script_tmpl = 'source "%s"'

        elif shell == 'cmd.exe':
            self.pathsep_join = ';'.join
            self.path_conversion = path_identity
            self.script_extension = '.bat'
            self.tempfile_extension = '.bat'
            self.shift_args = 1

            self.unset_var_tmpl = '@SET %s='
            self.set_var_tmpl = '@SET "%s=%s"'
            self.run_script_tmpl = '@CALL "%s"'

        elif shell == 'fish':
            self.pathsep_join = ' '.join
            self.path_conversion = native_path_to_unix
            self.script_extension = '.fish'
            self.tempfile_extension = None  # write instructions to stdout rather than a temp file
            self.shift_args = 0

            self.unset_var_tmpl = 'set -e %s'
            self.set_var_tmpl = 'set -gx %s "%s"'
            self.run_script_tmpl = 'source "%s"'

        elif shell == 'powershell':
            self.pathsep_join = ';'.join
            self.path_conversion = path_identity
            self.script_extension = '.ps1'
            self.tempfile_extension = None  # write instructions to stdout rather than a temp file
            self.shift_args = 0

            self.unset_var_tmpl = 'Remove-Variable %s'
            self.set_var_tmpl = '$env:%s = "%s"'
            self.run_script_tmpl = '. "%s"'

        else:
            raise NotImplementedError()

    def _finalize(self, commands, ext):
        commands = concatv(commands, ('',))  # add terminating newline
        if ext is None:
            return '\n'.join(commands)
        elif ext:
            with NamedTemporaryFile(suffix=ext, delete=False) as tf:
                tf.write(ensure_binary('\n'.join(commands)))
            return tf.name
        else:
            raise NotImplementedError()

    def activate(self):
        return self._finalize(self._yield_commands(self.build_activate(self.env_name_or_prefix)),
                              self.tempfile_extension)

    def deactivate(self):
        return self._finalize(self._yield_commands(self.build_deactivate()),
                              self.tempfile_extension)

    def reactivate(self):
        return self._finalize(self._yield_commands(self.build_reactivate()),
                              self.tempfile_extension)

    def execute(self):
        # return value meant to be written to stdout
        self._parse_and_set_args(self._raw_arguments)
        return getattr(self, self.command)()

    def _parse_and_set_args(self, arguments):
        # the first index of arguments MUST be either activate, deactivate, or reactivate
        if arguments is None:
            from .exceptions import ArgumentError
            raise ArgumentError("'activate', 'deactivate', or 'reactivate' command must be given")

        command = arguments[0]
        arguments = tuple(drop(self.shift_args + 1, arguments))
        help_flags = ('-h', '--help', '/?')
        non_help_args = tuple(arg for arg in arguments if arg not in help_flags)
        help_requested = len(arguments) != len(non_help_args)
        remainder_args = tuple(arg for arg in non_help_args if arg != command)

        if not command:
            from .exceptions import ArgumentError
            raise ArgumentError("'activate', 'deactivate', or 'reactivate' command must be given")
        elif help_requested:
            from . import CondaError
            class Help(CondaError):  # NOQA
                pass
            raise Help("help requested for %s" % command)
        elif command not in ('activate', 'deactivate', 'reactivate'):
            from .exceptions import ArgumentError
            raise ArgumentError("invalid command '%s'" % command)
        elif command == 'activate' and len(remainder_args) > 1:
            from .exceptions import ArgumentError
            raise ArgumentError('activate does not accept more than one argument')
        elif command != 'activate' and remainder_args:
            from .exceptions import ArgumentError
            raise ArgumentError('%s does not accept arguments' % command)

        if command == 'activate':
            self.env_name_or_prefix = remainder_args and remainder_args[0] or 'root'

        self.command = command

    def _yield_commands(self, cmds_dict):
        for key in sorted(cmds_dict.get('unset_vars', ())):
            yield self.unset_var_tmpl % key

        for key, value in sorted(iteritems(cmds_dict.get('set_vars', {}))):
            yield self.set_var_tmpl % (key, value)

        for script in cmds_dict.get('deactivate_scripts', ()):
            yield self.run_script_tmpl % script

        for script in cmds_dict.get('activate_scripts', ()):
            yield self.run_script_tmpl % script

    def build_activate(self, env_name_or_prefix):
        test_path = expand(env_name_or_prefix)
        if isdir(test_path):
            prefix = test_path
            if not isdir(join(prefix, 'conda-meta')):
                from .exceptions import EnvironmentLocationNotFound
                raise EnvironmentLocationNotFound(prefix)
        elif re.search(r'\\|/', env_name_or_prefix):
            prefix = env_name_or_prefix
            if not isdir(join(prefix, 'conda-meta')):
                from .exceptions import EnvironmentLocationNotFound
                raise EnvironmentLocationNotFound(prefix)
        else:
            from .base.context import locate_prefix_by_name
            prefix = locate_prefix_by_name(self.context, env_name_or_prefix)
        prefix = normpath(prefix)

        # query environment
        old_conda_shlvl = int(os.getenv('CONDA_SHLVL', 0))
        old_conda_prefix = os.getenv('CONDA_PREFIX')
        max_shlvl = self.context.max_shlvl

        if old_conda_prefix == prefix:
            return self.build_reactivate()
        elif os.getenv('CONDA_PREFIX_%s' % (old_conda_shlvl-1)) == prefix:
            # in this case, user is attempting to activate the previous environment,
            #  i.e. step back down
            return self.build_deactivate()

        join(prefix, 'etc', 'conda', 'activate.d', '*' + self.script_extension)
        activate_scripts = glob(join(
            prefix, 'etc', 'conda', 'activate.d', '*' + self.script_extension
        ))
        conda_default_env = self._default_env(prefix)
        conda_prompt_modifier = self._prompt_modifier(conda_default_env)

        assert 0 <= old_conda_shlvl <= max_shlvl
        if old_conda_shlvl == 0:
            new_path = self.pathsep_join(self._add_prefix_to_path(prefix))
            set_vars = {
                'CONDA_PYTHON_EXE': self.path_conversion(sys.executable),
                'PATH': new_path,
                'CONDA_PREFIX': self.path_conversion(prefix),
                'CONDA_SHLVL': old_conda_shlvl + 1,
                'CONDA_DEFAULT_ENV': conda_default_env,
                'CONDA_PROMPT_MODIFIER': conda_prompt_modifier,
            }
            deactivate_scripts = ()
        elif old_conda_shlvl == max_shlvl:
            new_path = self.pathsep_join(self._replace_prefix_in_path(old_conda_prefix, prefix))
            set_vars = {
                'PATH': new_path,
                'CONDA_PREFIX': self.path_conversion(prefix),
                'CONDA_DEFAULT_ENV': conda_default_env,
                'CONDA_PROMPT_MODIFIER': conda_prompt_modifier,
            }
            deactivate_scripts = glob(join(
                old_conda_prefix, 'etc', 'conda', 'deactivate.d', '*' + self.script_extension
            ))
        else:
            new_path = self.pathsep_join(self._add_prefix_to_path(prefix))
            set_vars = {
                'PATH': new_path,
                'CONDA_PREFIX': self.path_conversion(prefix),
                'CONDA_PREFIX_%d' % old_conda_shlvl: old_conda_prefix,
                'CONDA_SHLVL': old_conda_shlvl + 1,
                'CONDA_DEFAULT_ENV': conda_default_env,
                'CONDA_PROMPT_MODIFIER': conda_prompt_modifier,
            }
            deactivate_scripts = ()

        return {
            'unset_vars': (),
            'set_vars': set_vars,
            'deactivate_scripts': deactivate_scripts,
            'activate_scripts': activate_scripts,
        }

    def build_deactivate(self):
        # query environment
        old_conda_shlvl = int(os.getenv('CONDA_SHLVL', 0))
        old_conda_prefix = os.environ['CONDA_PREFIX']
        deactivate_scripts = self._get_deactivate_scripts(old_conda_prefix)

        new_conda_shlvl = old_conda_shlvl - 1
        new_path = self.pathsep_join(self._remove_prefix_from_path(old_conda_prefix))

        assert old_conda_shlvl > 0
        if old_conda_shlvl == 1:
            # TODO: warn conda floor
            unset_vars = (
                'CONDA_PREFIX',
                'CONDA_DEFAULT_ENV',
                'CONDA_PYTHON_EXE',
                'CONDA_PROMPT_MODIFIER',
            )
            set_vars = {
                'PATH': new_path,
                'CONDA_SHLVL': new_conda_shlvl,
            }
            activate_scripts = ()
        else:
            new_prefix = os.getenv('CONDA_PREFIX_%d' % new_conda_shlvl)
            conda_default_env = self._default_env(new_prefix)
            conda_prompt_modifier = self._prompt_modifier(conda_default_env)

            unset_vars = (
                'CONDA_PREFIX_%d' % new_conda_shlvl,
            )
            set_vars = {
                'PATH': new_path,
                'CONDA_SHLVL': new_conda_shlvl,
                'CONDA_PREFIX': new_prefix,
                'CONDA_DEFAULT_ENV': conda_default_env,
                'CONDA_PROMPT_MODIFIER': conda_prompt_modifier,
            }
            activate_scripts = self._get_activate_scripts(new_prefix)

        return {
            'unset_vars': unset_vars,
            'set_vars': set_vars,
            'deactivate_scripts': deactivate_scripts,
            'activate_scripts': activate_scripts,
        }

    def build_reactivate(self):
        conda_prefix = os.environ['CONDA_PREFIX']
        return {
            'unset_vars': (),
            'set_vars': {},
            'deactivate_scripts': self._get_deactivate_scripts(conda_prefix),
            'activate_scripts': self._get_activate_scripts(conda_prefix),
        }

    def _get_starting_path_list(self):
        path = os.environ['PATH']
        if on_win:
            # on Windows, the python interpreter prepends sys.prefix\Library\bin on startup WTF
            return path.split(os.pathsep)[1:]
        else:
            return path.split(os.pathsep)

    def _get_path_dirs(self, prefix):
        if on_win:  # pragma: unix no cover
            yield prefix.rstrip("\\")
            yield join(prefix, 'Library', 'mingw-w64', 'bin')
            yield join(prefix, 'Library', 'usr', 'bin')
            yield join(prefix, 'Library', 'bin')
            yield join(prefix, 'Scripts')
        else:
            yield join(prefix, 'bin')

    def _add_prefix_to_path(self, prefix, starting_path_dirs=None):
        if starting_path_dirs is None:
            starting_path_dirs = self._get_starting_path_list()
        return self.path_conversion(*tuple(concatv(
            self._get_path_dirs(prefix),
            starting_path_dirs,
        )))

    def _remove_prefix_from_path(self, prefix, starting_path_dirs=None):
        return self._replace_prefix_in_path(prefix, None, starting_path_dirs)

    def _replace_prefix_in_path(self, old_prefix, new_prefix, starting_path_dirs=None):
        if starting_path_dirs is None:
            path_list = self._get_starting_path_list()
        else:
            path_list = list(starting_path_dirs)
        if on_win:  # pragma: unix no cover
            # windows has a nasty habit of adding extra Library\bin directories
            prefix_dirs = tuple(self._get_path_dirs(old_prefix))
            try:
                first_idx = path_list.index(prefix_dirs[0])
            except ValueError:
                first_idx = 0
            else:
                last_idx = path_list.index(prefix_dirs[-1])
                del path_list[first_idx:last_idx+1]
            if new_prefix is not None:
                path_list[first_idx:first_idx] = list(self._get_path_dirs(new_prefix))
        else:
            try:
                idx = path_list.index(join(old_prefix, 'bin'))
            except ValueError:
                idx = 0
            else:
                del path_list[idx]
            if new_prefix is not None:
                path_list.insert(idx, join(new_prefix, 'bin'))
        return self.path_conversion(*path_list)

    def _default_env(self, prefix):
        if prefix == self.context.root_prefix:
            return 'root'
        return basename(prefix) if basename(dirname(prefix)) == 'envs' else prefix

    def _prompt_modifier(self, conda_default_env):
        return "(%s) " % conda_default_env if self.context.changeps1 else ""

    def _get_activate_scripts(self, prefix):
        return self.path_conversion(*glob(join(
            prefix, 'etc', 'conda', 'activate.d', '*' + self.script_extension
        )))

    def _get_deactivate_scripts(self, prefix):
        return self.path_conversion(*glob(join(
            prefix, 'etc', 'conda', 'deactivate.d', '*' + self.script_extension
        )))


def expand(path):
    return abspath(expanduser(expandvars(path)))


def ensure_binary(value):
    try:
        return value.encode('utf-8')
    except AttributeError:  # pragma: no cover
        # AttributeError: '<>' object has no attribute 'encode'
        # In this case assume already binary type and do nothing
        return value


def native_path_to_unix(*paths):  # pragma: unix no cover
    # on windows, uses cygpath to convert windows native paths to posix paths
    if not on_win:
        return path_identity(*paths)
    from subprocess import PIPE, Popen
    from shlex import split
    command = 'cygpath --path -f -'
    p = Popen(split(command), stdin=PIPE, stdout=PIPE, stderr=PIPE)
    joined = ("%s" % os.pathsep).join(paths)
    if hasattr(joined, 'encode'):
        joined = joined.encode('utf-8')
    stdout, stderr = p.communicate(input=joined)
    rc = p.returncode
    if rc != 0 or stderr:
        from subprocess import CalledProcessError
        message = "\n  stdout: %s\n  stderr: %s\n  rc: %s\n" % (stdout, stderr, rc)
        print(message, file=sys.stderr)
        raise CalledProcessError(rc, command, message)
    if hasattr(stdout, 'decode'):
        stdout = stdout.decode('utf-8')
    final = stdout.strip().split(':')
    return final[0] if len(final) == 1 else tuple(final)


def path_identity(*paths):
    return paths[0] if len(paths) == 1 else paths


on_win = bool(sys.platform == "win32")
PY2 = sys.version_info[0] == 2
if PY2:  # pragma: py3 no cover
    string_types = basestring,  # NOQA
    text_type = unicode  # NOQA

    def iteritems(d, **kw):
        return d.iteritems(**kw)
else:  # pragma: py2 no cover
    string_types = str,
    text_type = str

    def iteritems(d, **kw):
        return iter(d.items(**kw))


def main(argv=None):
    argv = argv or sys.argv
    assert len(argv) >= 3
    assert argv[1].startswith('shell.')
    shell = argv[1].replace('shell.', '', 1)
    activator_args = argv[2:]
    activator = Activator(shell, activator_args)
    try:
        sys.stdout.write(activator.execute())
        return 0
    except Exception as e:
        from . import CondaError
        if isinstance(e, CondaError):
            sys.stderr.write(text_type(e))
            return e.return_code
        else:
            raise


if __name__ == '__main__':
    sys.exit(main())
