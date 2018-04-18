# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from glob import glob
import os
from os.path import abspath, basename, dirname, expanduser, expandvars, isdir, join, normpath
import re
import sys
from tempfile import NamedTemporaryFile

from .base.context import ROOT_ENV_NAME, context, locate_prefix_by_name
context.__init__()  # oOn import, context does not include SEARCH_PATH. This line fixes that.

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
    #   export_vars
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
        self.shell = shell
        self._raw_arguments = arguments

        if PY2:
            self.environ = {ensure_fs_path_encoding(k): ensure_fs_path_encoding(v)
                            for k, v in iteritems(os.environ)}
        else:
            self.environ = os.environ.copy()

        if shell == 'posix':
            self.pathsep_join = ':'.join
            self.path_conversion = native_path_to_unix
            self.script_extension = '.sh'
            self.tempfile_extension = None  # write instructions to stdout rather than a temp file
            self.shift_args = 0
            self.command_join = '\n'

            self.unset_var_tmpl = '\\unset %s'
            self.export_var_tmpl = "\\export %s='%s'"
            self.set_var_tmpl = "%s='%s'"
            self.run_script_tmpl = '\\. "%s"'

        elif shell == 'csh':
            self.pathsep_join = ':'.join
            self.path_conversion = native_path_to_unix
            self.script_extension = '.csh'
            self.tempfile_extension = None  # write instructions to stdout rather than a temp file
            self.shift_args = 0
            self.command_join = ';\n'

            self.unset_var_tmpl = 'unsetenv %s'
            self.export_var_tmpl = 'setenv %s "%s"'
            self.set_var_tmpl = "set %s='%s'"
            self.run_script_tmpl = 'source "%s"'

        elif shell == 'xonsh':
            self.pathsep_join = ':'.join
            self.path_conversion = native_path_to_unix
            self.script_extension = '.xsh'
            self.tempfile_extension = '.xsh'
            self.shift_args = 0
            self.command_join = '\n'

            self.unset_var_tmpl = 'del $%s'
            self.export_var_tmpl = "$%s = '%s'"
            self.run_script_tmpl = 'source "%s"'

        elif shell == 'cmd.exe':
            self.pathsep_join = ';'.join
            self.path_conversion = path_identity
            self.script_extension = '.bat'
            self.tempfile_extension = '.bat'
            self.shift_args = 1
            self.command_join = '\r\n' if on_win else '\n'

            self.unset_var_tmpl = '@SET %s='
            self.export_var_tmpl = '@SET "%s=%s"'
            self.run_script_tmpl = '@CALL "%s"'

        elif shell == 'fish':
            self.pathsep_join = '" "'.join
            self.path_conversion = native_path_to_unix
            self.script_extension = '.fish'
            self.tempfile_extension = None  # write instructions to stdout rather than a temp file
            self.shift_args = 0
            self.command_join = ';\n'

            self.unset_var_tmpl = 'set -e %s'
            self.export_var_tmpl = 'set -gx %s "%s"'
            self.run_script_tmpl = 'source "%s"'

        elif shell == 'powershell':
            self.pathsep_join = ';'.join
            self.path_conversion = path_identity
            self.script_extension = '.ps1'
            self.tempfile_extension = None  # write instructions to stdout rather than a temp file
            self.shift_args = 0
            self.command_join = '\n'

            self.unset_var_tmpl = 'Remove-Variable %s'
            self.export_var_tmpl = '$env:%s = "%s"'
            self.run_script_tmpl = '. "%s"'

        else:
            raise NotImplementedError()

    def _finalize(self, commands, ext):
        commands = concatv(commands, ('',))  # add terminating newline
        if ext is None:
            return self.command_join.join(commands)
        elif ext:
            with NamedTemporaryFile('w+b', suffix=ext, delete=False) as tf:
                # the default mode is 'w+b', and universal new lines don't work in that mode
                # command_join should account for that
                tf.write(ensure_binary(self.command_join.join(commands)))
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
        remainder_args = tuple(arg for arg in non_help_args if arg and arg != command)

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
            raise ArgumentError('activate does not accept more than one argument:\n'
                                + str(remainder_args) + '\n')
        elif command != 'activate' and remainder_args:
            from .exceptions import ArgumentError
            raise ArgumentError('%s does not accept arguments\nremainder_args: %s\n'
                                % (command, remainder_args))

        if command == 'activate':
            self.env_name_or_prefix = remainder_args and remainder_args[0] or 'root'

        self.command = command

    def _yield_commands(self, cmds_dict):
        for script in cmds_dict.get('deactivate_scripts', ()):
            yield self.run_script_tmpl % script

        for key in sorted(cmds_dict.get('unset_vars', ())):
            yield self.unset_var_tmpl % key

        for key, value in sorted(iteritems(cmds_dict.get('set_vars', {}))):
            yield self.set_var_tmpl % (key, value)

        for key, value in sorted(iteritems(cmds_dict.get('export_vars', {}))):
            yield self.export_var_tmpl % (key, value)

        for script in cmds_dict.get('activate_scripts', ()):
            yield self.run_script_tmpl % script

    def build_activate(self, env_name_or_prefix):
        if re.search(r'\\|/', env_name_or_prefix):
            prefix = expand(env_name_or_prefix)
            if not isdir(join(prefix, 'conda-meta')):
                from .exceptions import EnvironmentLocationNotFound
                raise EnvironmentLocationNotFound(prefix)
        elif env_name_or_prefix in (ROOT_ENV_NAME, 'root'):
            prefix = context.root_prefix
        else:
            prefix = locate_prefix_by_name(env_name_or_prefix)
        prefix = normpath(prefix)

        # query environment
        old_conda_shlvl = int(self.environ.get('CONDA_SHLVL', 0))
        old_conda_prefix = self.environ.get('CONDA_PREFIX')
        max_shlvl = context.max_shlvl

        if old_conda_prefix == prefix and old_conda_shlvl > 0:
            return self.build_reactivate()
        if self.environ.get('CONDA_PREFIX_%s' % (old_conda_shlvl-1)) == prefix:
            # in this case, user is attempting to activate the previous environment,
            #  i.e. step back down
            return self.build_deactivate()

        activate_scripts = self._get_activate_scripts(prefix)
        conda_default_env = self._default_env(prefix)
        conda_prompt_modifier = self._prompt_modifier(conda_default_env)

        assert 0 <= old_conda_shlvl <= max_shlvl
        set_vars = {}
        if old_conda_shlvl == 0:
            new_path = self.pathsep_join(self._add_prefix_to_path(prefix))
            export_vars = {
                'CONDA_PYTHON_EXE': self.path_conversion(sys.executable),
                'CONDA_EXE': self.path_conversion(context.conda_exe),
                'PATH': new_path,
                'CONDA_PREFIX': prefix,
                'CONDA_SHLVL': old_conda_shlvl + 1,
                'CONDA_DEFAULT_ENV': conda_default_env,
                'CONDA_PROMPT_MODIFIER': conda_prompt_modifier,
            }
            deactivate_scripts = ()
        elif old_conda_shlvl == max_shlvl:
            new_path = self.pathsep_join(self._replace_prefix_in_path(old_conda_prefix, prefix))
            export_vars = {
                'PATH': new_path,
                'CONDA_PREFIX': prefix,
                'CONDA_DEFAULT_ENV': conda_default_env,
                'CONDA_PROMPT_MODIFIER': conda_prompt_modifier,
            }
            deactivate_scripts = self._get_deactivate_scripts(old_conda_prefix)
        else:
            new_path = self.pathsep_join(self._add_prefix_to_path(prefix))
            export_vars = {
                'PATH': new_path,
                'CONDA_PREFIX': prefix,
                'CONDA_PREFIX_%d' % old_conda_shlvl: old_conda_prefix,
                'CONDA_SHLVL': old_conda_shlvl + 1,
                'CONDA_DEFAULT_ENV': conda_default_env,
                'CONDA_PROMPT_MODIFIER': conda_prompt_modifier,
            }
            deactivate_scripts = ()

        self._update_prompt(set_vars, conda_prompt_modifier)

        if on_win and self.shell == 'cmd.exe':
            import ctypes
            export_vars.update({
                "PYTHONIOENCODING": ctypes.cdll.kernel32.GetACP(),
            })

        return {
            'unset_vars': (),
            'set_vars': set_vars,
            'export_vars': export_vars,
            'deactivate_scripts': deactivate_scripts,
            'activate_scripts': activate_scripts,
        }

    def build_deactivate(self):
        # query environment
        old_conda_prefix = self.environ.get('CONDA_PREFIX')
        old_conda_shlvl = int(self.environ.get('CONDA_SHLVL', 0))
        if not old_conda_prefix or old_conda_shlvl < 1:
            # no active environment, so cannot deactivate; do nothing
            return {
                'unset_vars': (),
                'set_vars': {},
                'export_vars': {},
                'deactivate_scripts': (),
                'activate_scripts': (),
            }
        deactivate_scripts = self._get_deactivate_scripts(old_conda_prefix)

        new_conda_shlvl = old_conda_shlvl - 1
        new_path = self.pathsep_join(self._remove_prefix_from_path(old_conda_prefix))

        set_vars = {}
        if old_conda_shlvl == 1:
            # TODO: warn conda floor
            conda_prompt_modifier = ''
            unset_vars = (
                'CONDA_PREFIX',
                'CONDA_DEFAULT_ENV',
                'CONDA_PYTHON_EXE',
                'CONDA_EXE',
                'CONDA_PROMPT_MODIFIER',
            )
            export_vars = {
                'PATH': new_path,
                'CONDA_SHLVL': new_conda_shlvl,
            }
            activate_scripts = ()
        else:
            new_prefix = self.environ.get('CONDA_PREFIX_%d' % new_conda_shlvl)
            conda_default_env = self._default_env(new_prefix)
            conda_prompt_modifier = self._prompt_modifier(conda_default_env)

            unset_vars = (
                'CONDA_PREFIX_%d' % new_conda_shlvl,
            )
            export_vars = {
                'PATH': new_path,
                'CONDA_SHLVL': new_conda_shlvl,
                'CONDA_PREFIX': new_prefix,
                'CONDA_DEFAULT_ENV': conda_default_env,
                'CONDA_PROMPT_MODIFIER': conda_prompt_modifier,
            }
            activate_scripts = self._get_activate_scripts(new_prefix)

        self._update_prompt(set_vars, conda_prompt_modifier)

        return {
            'unset_vars': unset_vars,
            'set_vars': set_vars,
            'export_vars': export_vars,
            'deactivate_scripts': deactivate_scripts,
            'activate_scripts': activate_scripts,
        }

    def build_reactivate(self):
        conda_prefix = self.environ.get('CONDA_PREFIX')
        conda_shlvl = int(self.environ.get('CONDA_SHLVL', 0))
        if not conda_prefix or conda_shlvl < 1:
            # no active environment, so cannot reactivate; do nothing
            return {
                'unset_vars': (),
                'set_vars': {},
                'export_vars': {},
                'deactivate_scripts': (),
                'activate_scripts': (),
            }
        conda_default_env = self.environ.get('CONDA_DEFAULT_ENV', self._default_env(conda_prefix))
        new_path = self.pathsep_join(self._replace_prefix_in_path(conda_prefix, conda_prefix))
        set_vars = {}
        conda_prompt_modifier = self._prompt_modifier(conda_default_env)
        self._update_prompt(set_vars, conda_prompt_modifier)
        # environment variables are set only to aid transition from conda 4.3 to conda 4.4
        return {
            'unset_vars': (),
            'set_vars': set_vars,
            'export_vars': {
                'PATH': new_path,
                'CONDA_SHLVL': conda_shlvl,
                'CONDA_PROMPT_MODIFIER': self._prompt_modifier(conda_default_env),
            },
            'deactivate_scripts': self._get_deactivate_scripts(conda_prefix),
            'activate_scripts': self._get_activate_scripts(conda_prefix),
        }

    def _get_starting_path_list(self):
        path = self.environ['PATH']
        if on_win:
            # On Windows, the Anaconda Python interpreter prepends sys.prefix\Library\bin on
            # startup. It's a hack that allows users to avoid using the correct activation
            # procedure; a hack that needs to go away because it doesn't add all the paths.
            # See: https://github.com/AnacondaRecipes/python-feedstock/blob/master/recipe/0005-Win32-Ensure-Library-bin-is-in-os.environ-PATH.patch  # NOQA
            # But, we now detect if that has happened because:
            #   1. In future we would like to remove this hack and require real activation.
            #   2. We should not assume that the Anaconda Python interpreter is being used.
            path_split = path.split(os.pathsep)
            library_bin = r"%s\Library\bin" % (sys.prefix)
            # ^^^ deliberately the same as: https://github.com/AnacondaRecipes/python-feedstock/blob/8e8aee4e2f4141ecfab082776a00b374c62bb6d6/recipe/0005-Win32-Ensure-Library-bin-is-in-os.environ-PATH.patch#L20  # NOQA
            if normpath(path_split[0]) == normpath(library_bin):
                return path_split[1:]
            else:
                return path_split
        else:
            return path.split(os.pathsep)

    @staticmethod
    def _get_path_dirs(prefix):
        if on_win:  # pragma: unix no cover
            yield prefix.rstrip("\\")
            yield join(prefix, 'Library', 'mingw-w64', 'bin')
            yield join(prefix, 'Library', 'usr', 'bin')
            yield join(prefix, 'Library', 'bin')
            yield join(prefix, 'Scripts')
            yield join(prefix, 'bin')
        else:
            yield join(prefix, 'bin')

    def _add_prefix_to_path(self, prefix, starting_path_dirs=None):
        if starting_path_dirs is None:
            starting_path_dirs = self._get_starting_path_list()
        return self.path_conversion(concatv(
            self._get_path_dirs(prefix),
            starting_path_dirs,
        ))

    def _remove_prefix_from_path(self, prefix, starting_path_dirs=None):
        return self._replace_prefix_in_path(prefix, None, starting_path_dirs)

    def _replace_prefix_in_path(self, old_prefix, new_prefix, starting_path_dirs=None):
        if starting_path_dirs is None:
            path_list = self._get_starting_path_list()
        else:
            path_list = list(starting_path_dirs)
        if on_win:  # pragma: unix no cover
            if old_prefix is not None:
                # windows has a nasty habit of adding extra Library\bin directories
                prefix_dirs = tuple(self._get_path_dirs(old_prefix))
                try:
                    first_idx = path_list.index(prefix_dirs[0])
                except ValueError:
                    first_idx = 0
                else:
                    last_idx = path_list.index(prefix_dirs[-1])
                    del path_list[first_idx:last_idx+1]
            else:
                first_idx = 0
            if new_prefix is not None:
                path_list[first_idx:first_idx] = list(self._get_path_dirs(new_prefix))
        else:
            if old_prefix is not None:
                try:
                    idx = path_list.index(join(old_prefix, 'bin'))
                except ValueError:
                    idx = 0
                else:
                    del path_list[idx]
            else:
                idx = 0
            if new_prefix is not None:
                path_list.insert(idx, join(new_prefix, 'bin'))
        return self.path_conversion(path_list)

    def _update_prompt(self, set_vars, conda_prompt_modifier):
        if not context.changeps1:
            return

        if self.shell == 'posix':
            ps1 = self.environ.get('PS1', '')
            current_prompt_modifier = self.environ.get('CONDA_PROMPT_MODIFIER')
            if current_prompt_modifier:
                ps1 = re.sub(re.escape(current_prompt_modifier), r'', ps1)
            # Because we're using single-quotes to set shell variables, we need to handle the
            # proper escaping of single quotes that are already part of the string.
            # Best solution appears to be https://stackoverflow.com/a/1250279
            ps1 = ps1.replace("'", "'\"'\"'")
            set_vars.update({
                'PS1': conda_prompt_modifier + ps1,
            })
        elif self.shell == 'csh':
            prompt = self.environ.get('prompt', '')
            current_prompt_modifier = self.environ.get('CONDA_PROMPT_MODIFIER')
            if current_prompt_modifier:
                prompt = re.sub(re.escape(current_prompt_modifier), r'', prompt)
            set_vars.update({
                'prompt': conda_prompt_modifier + prompt,
            })

    def _default_env(self, prefix):
        if prefix == context.root_prefix:
            return 'base'
        return basename(prefix) if basename(dirname(prefix)) == 'envs' else prefix

    def _prompt_modifier(self, conda_default_env):
        return "(%s) " % conda_default_env if context.changeps1 else ""

    def _get_activate_scripts(self, prefix):
        return self.path_conversion(sorted(glob(join(
            prefix, 'etc', 'conda', 'activate.d', '*' + self.script_extension
        ))))

    def _get_deactivate_scripts(self, prefix):
        return self.path_conversion(sorted(glob(join(
            prefix, 'etc', 'conda', 'deactivate.d', '*' + self.script_extension
        )), reverse=True))


def expand(path):
    return abspath(expanduser(expandvars(path)))


def ensure_binary(value):
    try:
        return value.encode('utf-8')
    except AttributeError:  # pragma: no cover
        # AttributeError: '<>' object has no attribute 'encode'
        # In this case assume already binary type and do nothing
        return value


def ensure_fs_path_encoding(value):
    try:
        return value.decode(FILESYSTEM_ENCODING)
    except AttributeError:
        return value


def native_path_to_unix(paths):  # pragma: unix no cover
    # on windows, uses cygpath to convert windows native paths to posix paths
    if not on_win:
        return path_identity(paths)
    from subprocess import PIPE, Popen
    from shlex import split
    command = 'cygpath --path -f -'
    p = Popen(split(command), stdin=PIPE, stdout=PIPE, stderr=PIPE)

    single_path = isinstance(paths, string_types)
    joined = paths if single_path else ("%s" % os.pathsep).join(paths)

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
    stdout = stdout.strip()
    final = stdout and stdout.split(':') or ()
    return final[0] if single_path else tuple(final)


def path_identity(paths):
    return paths if isinstance(paths, string_types) else tuple(paths)


on_win = bool(sys.platform == "win32")
PY2 = sys.version_info[0] == 2
FILESYSTEM_ENCODING = sys.getfilesystemencoding()
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
    from .common.compat import init_std_stream_encoding

    init_std_stream_encoding()
    argv = argv or sys.argv
    assert len(argv) >= 3
    assert argv[1].startswith('shell.')
    shell = argv[1].replace('shell.', '', 1)
    activator_args = argv[2:]
    activator = Activator(shell, activator_args)
    try:
        print(activator.execute(), end='')
        return 0
    except Exception as e:
        from . import CondaError
        if isinstance(e, CondaError):
            print(text_type(e), file=sys.stderr)
            return e.return_code
        else:
            raise


if __name__ == '__main__':
    sys.exit(main())
