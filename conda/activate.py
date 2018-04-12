# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from glob import glob
import os
from os.path import abspath, basename, dirname, expanduser, expandvars, isdir, join, normpath
import re
import sys
from tempfile import NamedTemporaryFile

from .base.context import ROOT_ENV_NAME, context, locate_prefix_by_name
context.__init__()  # On import, context does not include SEARCH_PATH. This line fixes that.

try:
    from cytoolz.itertoolz import concatv, drop
except ImportError:  # pragma: no cover
    from ._vendor.toolz.itertoolz import concatv, drop  # NOQA


class _Activator(object):
    # Activate and deactivate have three tasks
    #   1. Set and unset environment variables
    #   2. Execute/source activate.d/deactivate.d scripts
    #   3. Update the command prompt
    #
    # Shells should also use 'reactivate' following conda's install, update, and
    #   remove/uninstall commands.
    #
    # All core logic is in the build_*() functions:
    #   - build_activate()
    #   - build_deactivate()
    #   - build_reactivate()
    #   - build_post()
    # and is independent of shell type.  Each returns a map optionally containing the keys:
    #   unset_vars          (tuple of keys to unset)
    #   export_vars         (dict of key-values to export)
    #   set_vars            (dict of key-values to set)
    #   activate_scripts    (tuple of activate scripts)
    #   deactivate_scripts  (tuple of deactivate scripts)
    #   post                (bool to include post command)
    #
    # The value of the CONDA_PROMPT_MODIFIER environment variable holds conda's contribution
    #   to the command prompt.
    #
    # To implement support for a new shell, ideally one would only need to add shell-specific
    # information to the __init__ method of this class.

    # The following instance variables must be defined by each implementation.
    shell = None
    pathsep_join = None
    path_conversion = None
    script_extension = None
    tempfile_extension = None  # None means write instructions to stdout rather than a temp file
    shift_args = None
    command_join = None

    unset_var_tmpl = None
    export_var_tmpl = None
    set_var_tmpl = None
    run_script_tmpl = None

    def __init__(self, arguments=None):
        self._raw_arguments = arguments

        if PY2:
            self.environ = {ensure_fs_path_encoding(k): ensure_fs_path_encoding(v)
                            for k, v in iteritems(os.environ)}
        else:
            self.environ = os.environ.copy()

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

    def post(self):
        return self._finalize(self._yield_commands(self.build_post()),
                              self.tempfile_extension)

    def execute(self):
        # return value meant to be written to stdout
        self._parse_and_set_args(self._raw_arguments)
        return getattr(self, self.command)()

    def _parse_and_set_args(self, arguments):
        # the first index of arguments MUST be either activate, deactivate, or reactivate
        if arguments is None:
            from .exceptions import ArgumentError
            raise ArgumentError("'activate', 'deactivate', 'reactivate', or 'post' command must "
                                "be given")

        command = arguments[0]
        arguments = tuple(drop(self.shift_args + 1, arguments))
        help_flags = ('-h', '--help', '/?')
        non_help_args = tuple(arg for arg in arguments if arg not in help_flags)
        help_requested = len(arguments) != len(non_help_args)
        remainder_args = tuple(arg for arg in non_help_args if arg and arg != command)

        if not command:
            from .exceptions import ArgumentError
            raise ArgumentError("'activate', 'deactivate', 'reactivate', or 'post' command must "
                                "be given")
        elif help_requested:
            from . import CondaError
            class Help(CondaError):  # NOQA
                pass
            raise Help("help requested for %s" % command)
        elif command not in ('activate', 'deactivate', 'reactivate', 'post'):
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

        if cmds_dict.get('post', False):
            yield self.post_tmpl

        for script in cmds_dict.get('activate_scripts', ()):
            yield self.run_script_tmpl % script

    def build_activate(self, env_name_or_prefix):
        # determine the environment prefix (the path to the environment) that we are activating
        if re.search(r'\\|/', env_name_or_prefix):
            new_prefix = expand(env_name_or_prefix)
            if not isdir(join(new_prefix, 'conda-meta')):
                from .exceptions import EnvironmentLocationNotFound
                raise EnvironmentLocationNotFound(new_prefix)
        elif env_name_or_prefix in (ROOT_ENV_NAME, 'root'):
            new_prefix = context.root_prefix
        else:
            new_prefix = locate_prefix_by_name(env_name_or_prefix)
        new_prefix = normpath(new_prefix)

        # query environment/context
        old_shlvl = int(self.environ.get('CONDA_SHLVL', 0))
        old_prefix = self.environ.get('CONDA_PREFIX')
        max_shlvl = context.max_shlvl

        if old_prefix == new_prefix and old_shlvl > 0:
            # user is attempting to activate the currently active environment, use reactivate
            # instead
            return self.build_reactivate()
        if self.environ.get('CONDA_PREFIX_%s' % (old_shlvl - 1)) == new_prefix:
            # in this case, user is attempting to activate the previous environment,
            # i.e. step back down
            return self.build_deactivate()
        assert 0 <= old_shlvl <= max_shlvl

        conda_default_env = self._default_env(new_prefix)
        conda_prompt_modifier = self._prompt_modifier(conda_default_env)

        if old_shlvl == 0:
            # this is the first activate (in most cases this is "base")
            export_vars = {
                'CONDA_PYTHON_EXE': self.path_conversion(sys.executable),
                'CONDA_EXE': self.path_conversion(context.conda_exe),
                'CONDA_PREFIX': new_prefix,
                'CONDA_SHLVL': old_shlvl + 1,
                'CONDA_DEFAULT_ENV': conda_default_env,
                'CONDA_PROMPT_MODIFIER': conda_prompt_modifier,
            }
        elif old_shlvl == max_shlvl:
            # this is the top of the activate stack, we are effectively replacing the previously
            # activated environment
            export_vars = {
                'CONDA_PREFIX': new_prefix,
                'CONDA_DEFAULT_ENV': conda_default_env,
                'CONDA_PROMPT_MODIFIER': conda_prompt_modifier,
            }
        else:
            # this is not the top of the activate stack, we are effectively appending this activate
            # to the previous activate
            export_vars = {
                'CONDA_PREFIX': new_prefix,
                'CONDA_PREFIX_%d' % old_shlvl: old_prefix,
                'CONDA_SHLVL': old_shlvl + 1,
                'CONDA_DEFAULT_ENV': conda_default_env,
                'CONDA_PROMPT_MODIFIER': conda_prompt_modifier,
            }

        # get deactivate_scripts and whether post needs to occur
        deactivate_scripts = self._get_deactivate_scripts(old_prefix)
        post = self._derive_post_from_deactivate(deactivate_scripts, export_vars,
                                                 old_prefix=old_prefix,
                                                 new_prefix=new_prefix)

        # update the prompt
        set_vars = {}
        if context.changeps1:
            self._update_prompt(set_vars, conda_prompt_modifier)

        self._build_activate_shell_custom(export_vars)

        return {
            'deactivate_scripts': deactivate_scripts,
            'set_vars': set_vars,
            'export_vars': export_vars,
            'post': post,
            'activate_scripts': self._get_activate_scripts(new_prefix),
        }

    def build_deactivate(self):
        # query environment
        old_prefix = self.environ.get('CONDA_PREFIX')
        old_shlvl = int(self.environ.get('CONDA_SHLVL', 0))
        if not old_prefix or old_shlvl < 1:
            # no active environment, so cannot deactivate; do nothing
            return {}

        new_shlvl = old_shlvl - 1

        if old_shlvl == 1:
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
                'CONDA_SHLVL': new_shlvl,
            }
            activate_scripts = ()
        else:
            new_prefix = self.environ.get('CONDA_PREFIX_%d' % new_shlvl)
            conda_default_env = self._default_env(new_prefix)
            conda_prompt_modifier = self._prompt_modifier(conda_default_env)

            unset_vars = (
                'CONDA_PREFIX_%d' % new_shlvl,
            )
            export_vars = {
                'CONDA_SHLVL': new_shlvl,
                'CONDA_PREFIX': new_prefix,
                'CONDA_DEFAULT_ENV': conda_default_env,
                'CONDA_PROMPT_MODIFIER': conda_prompt_modifier,
            }
            activate_scripts = self._get_activate_scripts(new_prefix)

        # get deactivate_scripts and whether post needs to occur
        deactivate_scripts = self._get_deactivate_scripts(old_prefix)
        # there is no new_prefix as we are deactivating, which always pops a prefix, the "new"
        # prefix is already on the $PATH
        post = self._derive_post_from_deactivate(deactivate_scripts, export_vars,
                                                 old_prefix=old_prefix,
                                                 new_prefix="")

        # update the prompt
        set_vars = {}
        if context.changeps1:
            self._update_prompt(set_vars, conda_prompt_modifier)

        return {
            'deactivate_scripts': deactivate_scripts,
            'unset_vars': unset_vars,
            'set_vars': set_vars,
            'export_vars': export_vars,
            'post': post,
            'activate_scripts': activate_scripts,
        }

    def build_reactivate(self):
        prefix = self.environ.get('CONDA_PREFIX')
        shlvl = int(self.environ.get('CONDA_SHLVL', -1))
        if not prefix or shlvl < 1:
            # no active environment, so cannot reactivate; do nothing
            return {}

        conda_default_env = self.environ.get('CONDA_DEFAULT_ENV', self._default_env(prefix))
        conda_prompt_modifier = self._prompt_modifier(conda_default_env)

        # environment variables are set only to aid transition from conda 4.3 to conda 4.4
        export_vars = {
            'CONDA_SHLVL': shlvl,
            'CONDA_PROMPT_MODIFIER': conda_prompt_modifier,
        }

        # get deactivate_scripts and whether post needs to occur
        deactivate_scripts = self._get_deactivate_scripts(prefix)
        post = self._derive_post_from_deactivate(deactivate_scripts, export_vars,
                                                 old_prefix=prefix,
                                                 new_prefix=prefix)

        # update the prompt
        set_vars = {}
        if context.changeps1:
            self._update_prompt(set_vars, conda_prompt_modifier)

        return {
            'deactivate_scripts': deactivate_scripts,
            'set_vars': set_vars,
            'export_vars': export_vars,
            'post': post,
            'activate_scripts': self._get_activate_scripts(prefix),
        }

    def build_post(self):
        conda_post = self.environ.get("CONDA_POST")
        if not conda_post:
            # no post process defined
            return {}

        # create the export_vars
        export_vars = {}
        old_prefix, new_prefix = conda_post.split(":")
        self._update_path(export_vars, old_prefix, new_prefix)

        # create the unset_vars
        unset_vars = ("CONDA_POST",)

        return {
            'unset_vars': unset_vars,
            'export_vars': export_vars,
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

    def _build_activate_shell_custom(self, export_vars):
        # A method that can be overriden by shell-specific implementations.
        # The signature of this method may change in the future.
        pass

    def _update_prompt(self, set_vars, conda_prompt_modifier):
        pass

    def _derive_post_from_deactivate(self, deactivate_scripts, export_vars,
                                     old_prefix="", new_prefix=""):
        # determine how to handle the $PATH based on whether deactivate scripts exist
        if deactivate_scripts:
            # there are deactivate scripts, we need to use the post process to fixup the $PATH
            #
            # there is no new_prefix as we are deactivating, which always pops a prefix, the "new"
            # prefix is already on the $PATH
            old_prefix = old_prefix if old_prefix else ''
            new_prefix = new_prefix if new_prefix else ''
            export_vars["CONDA_POST"] = "%s:%s" % (old_prefix, new_prefix)
            return True
        else:
            # there are no deactivate scripts, we need to update the $PATH in the current process
            #
            # there is no new_prefix as we are deactivating, which always pops a prefix, the "new"
            # prefix is already on the $PATH
            self._update_path(export_vars, old_prefix, new_prefix)
            return False

    def _update_path(self, export_vars, old_prefix=None, new_prefix=None):
        # determine what kind of $PATH modification to make
        if not old_prefix and new_prefix:
            # adding new prefix to $PATH
            path = self._add_prefix_to_path(new_prefix)
        elif old_prefix and new_prefix:
            # replacing old prefix with new prefix in $PATH
            path = self._replace_prefix_in_path(old_prefix, new_prefix)
        elif old_prefix and not new_prefix:
            # removing old prefix from $PATH
            path = self._remove_prefix_from_path(old_prefix)

        # add the new path to export_vars
        export_vars["PATH"] = self.pathsep_join(path)

    def _default_env(self, prefix):
        if prefix == context.root_prefix:
            return 'base'
        return basename(prefix) if basename(dirname(prefix)) == 'envs' else prefix

    def _prompt_modifier(self, conda_default_env):
        return "(%s) " % conda_default_env if context.changeps1 else ""

    def _get_activate_scripts(self, prefix):
        if not prefix:
            return ()
        return self.path_conversion(glob(join(
            prefix, 'etc', 'conda', 'activate.d', '*' + self.script_extension
        )))

    def _get_deactivate_scripts(self, prefix):
        if not prefix:
            return ()
        return self.path_conversion(glob(join(
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


class PosixActivator(_Activator):

    def __init__(self, arguments=None):
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

        self.post_tmpl = "\n".join((
            '\local ask_conda',
            'ask_conda="$(PS1="${PS1}" "${_CONDA_EXE}" shell.posix post)" || \\return $?',
            '\eval "${ask_conda}"'))

        super(PosixActivator, self).__init__(arguments)

    def _update_prompt(self, set_vars, conda_prompt_modifier):
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


class CshActivator(_Activator):

    def __init__(self, arguments=None):
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

        self.post_tmpl = "\n".join((
            ('set ask_conda="`('
                "setenv prompt '${prompt}' ; ${_CONDA_EXE}' shell.csh post"
             ')`" || exit ${status}'),
            'eval "${ask_conda}"'))

        super(CshActivator, self).__init__(arguments)

    def _update_prompt(self, set_vars, conda_prompt_modifier):
        prompt = self.environ.get('prompt', '')
        current_prompt_modifier = self.environ.get('CONDA_PROMPT_MODIFIER')
        if current_prompt_modifier:
            prompt = re.sub(re.escape(current_prompt_modifier), r'', prompt)
        set_vars.update({
            'prompt': conda_prompt_modifier + prompt,
        })


class XonshActivator(_Activator):

    def __init__(self, arguments=None):
        self.pathsep_join = ':'.join
        self.path_conversion = native_path_to_unix
        self.script_extension = '.xsh'
        self.tempfile_extension = '.xsh'
        self.shift_args = 0
        self.command_join = '\n'

        self.unset_var_tmpl = 'del $%s'
        self.export_var_tmpl = "$%s = '%s'"
        self.set_var_tmpl = "$%s = '%s'"  # TODO: determine if different than export_var_tmpl
        self.run_script_tmpl = 'source "%s"'

        self.post_tmpl = "\n".join((
            "pipeline2 = !(@(_CONDA_EXE) shell.xonsh post)",
            "stdout2 = _raise_pipeline_error(pipeline2)",
            "source @(stdout2)",
            "os.unlink(stdout2)"))

        super(XonshActivator, self).__init__(arguments)


class CmdExeActivator(_Activator):

    def __init__(self, arguments=None):
        self.pathsep_join = ';'.join
        self.path_conversion = path_identity
        self.script_extension = '.bat'
        self.tempfile_extension = '.bat'
        self.shift_args = 1
        self.command_join = '\r\n' if on_win else '\n'

        self.unset_var_tmpl = '@SET %s='
        self.export_var_tmpl = '@SET "%s=%s"'
        self.set_var_tmpl = '@SET "%s=%s"'  # TODO: determine if different than export_var_tmpl
        self.run_script_tmpl = '@CALL "%s"'

        self.post_tmpl = "\n".join((
            ('@FOR /F "delims=" %%i IN ('
                "'@CALL %_CONDA_EXE% shell.cmd.exe post %*'"
             ') DO @SET "_TEMP_SCRIPT_PATH=%%i"'),
            '@IF "%_TEMP_SCRIPT_PATH%"=="" GOTO :ErrorEnd',
            '@CALL "%_TEMP_SCRIPT_PATH%"',
            '@DEL /F /Q "%_TEMP_SCRIPT_PATH%"',
            '@SET _TEMP_SCRIPT_PATH=',
            '@SET _CONDA_POST=',
            '',
            '@GOTO :End',
            '',
            ':End',
            '@SET _CONDA_EXE=',
            '@GOTO :EOF',
            '',
            ':ErrorEnd',
            '@SET _CONDA_EXE=',
            '@EXIT /B 1'))

        super(CmdExeActivator, self).__init__(arguments)

    def _build_activate_shell_custom(self, export_vars):
        if on_win:
            import ctypes
            export_vars.update({
                "PYTHONIOENCODING": ctypes.cdll.kernel32.GetACP(),
            })


class FishActivator(_Activator):

    def __init__(self, arguments=None):
        self.pathsep_join = '" "'.join
        self.path_conversion = native_path_to_unix
        self.script_extension = '.fish'
        self.tempfile_extension = None  # write instructions to stdout rather than a temp file
        self.shift_args = 0
        self.command_join = ';\n'

        self.unset_var_tmpl = 'set -e %s'
        self.export_var_tmpl = 'set -gx %s "%s"'
        self.set_var_tmpl = 'set -gx %s "%s"'  # TODO: determine if different than export_var_tmpl
        self.run_script_tmpl = 'source "%s"'

        self.post_tmpl = "\n".join((
            "eval (eval $_CONDA_EXE shell.fish post)",))

        super(FishActivator, self).__init__(arguments)


class PowershellActivator(_Activator):

    def __init__(self, arguments=None):
        self.pathsep_join = ';'.join
        self.path_conversion = path_identity
        self.script_extension = '.ps1'
        self.tempfile_extension = None  # write instructions to stdout rather than a temp file
        self.shift_args = 0
        self.command_join = '\n'

        self.unset_var_tmpl = 'Remove-Variable %s'
        self.export_var_tmpl = '$env:%s = "%s"'
        self.set_var_tmpl = '$env:%s = "%s"'  # TODO: determine if different than export_var_tmpl
        self.run_script_tmpl = '. "%s"'

        self.post_tmpl = "\n".join((
                "",))

        super(PowershellActivator, self).__init__(arguments)


activator_map = {
    'posix': PosixActivator,
    'csh': CshActivator,
    'xonsh': XonshActivator,
    'cmd.exe': CmdExeActivator,
    'fish': FishActivator,
    'powershell': PowershellActivator,
}


def main(argv=None):
    from .common.compat import init_std_stream_encoding

    init_std_stream_encoding()
    argv = argv or sys.argv
    assert len(argv) >= 3
    assert argv[1].startswith('shell.')
    shell = argv[1].replace('shell.', '', 1)
    activator_args = argv[2:]
    try:
        activator_cls = activator_map[shell]
    except KeyError:
        from . import CondaError
        raise CondaError("%s is not a supported shell." % shell)
    activator = activator_cls(activator_args)
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
