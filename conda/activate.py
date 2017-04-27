# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from glob import glob
import os
from os.path import abspath, basename, dirname, expanduser, expandvars, isdir, join
import re
import sys
from tempfile import NamedTemporaryFile

try:
    from cytoolz.itertoolz import concatv
except ImportError:  # pragma: no cover
    from ._vendor.toolz.itertoolz import concatv  # NOQA


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

    def __init__(self, shell):
        from .base.context import context
        self.context = context
        self.shell = shell

        if shell == 'posix':
            self.pathsep_join = ':'.join
            self.path_conversion = native_path_to_unix
            self.script_extension = '.sh'
            self.finalizer_extension = None  # don't write to file

            self.unset_var_tmpl = 'unset %s'
            self.set_var_tmpl = 'export %s="%s"'
            self.run_script_tmpl = '. "%s"'

        elif shell == 'csh':
            self.pathsep_join = ':'.join
            self.path_conversion = native_path_to_unix
            self.script_extension = '.csh'
            self.finalizer_extension = None  # don't write to file

            self.unset_var_tmpl = 'unset %s'
            self.set_var_tmpl = 'setenv %s "%s"'
            self.run_script_tmpl = 'source "%s"'

        elif shell == 'xonsh':
            self.pathsep_join = ':'.join
            self.path_conversion = native_path_to_unix
            self.script_extension = '.xsh'
            self.finalizer_extension = '.xsh'

            self.unset_var_tmpl = 'del $%s'
            self.set_var_tmpl = '$%s = "%s"'
            self.run_script_tmpl = 'source "%s"'

        else:
            raise NotImplementedError()

    def _finalize(self, commands, ext):
        if ext is None:
            return '\n'.join(commands)
        elif ext:
            with NamedTemporaryFile(suffix=ext, delete=False) as tf:
                tf.write(ensure_binary('\n'.join(commands)))
                tf.write(ensure_binary('\n'))
            return tf.name
        else:
            raise NotImplementedError()

    def activate(self, name_or_prefix):
        return self._finalize(self._yield_commands(self.build_activate(name_or_prefix)),
                              self.finalizer_extension)

    def deactivate(self):
        return self._finalize(self._yield_commands(self.build_deactivate()),
                              self.finalizer_extension)

    def reactivate(self):
        return self._finalize(self._yield_commands(self.build_reactivate()),
                              self.finalizer_extension)

    def _yield_commands(self, cmds_dict):
        for key in sorted(cmds_dict.get('unset_vars', ())):
            yield self.unset_var_tmpl % key

        for key, value in sorted(iteritems(cmds_dict.get('set_vars', {}))):
            yield self.set_var_tmpl % (key, value)

        for script in cmds_dict.get('deactivate_scripts', ()):
            yield self.run_script_tmpl % script

        for script in cmds_dict.get('activate_scripts', ()):
            yield self.run_script_tmpl % script

    def build_activate(self, name_or_prefix):
        test_path = expand(name_or_prefix)
        if isdir(test_path):
            prefix = test_path
            if not isdir(join(prefix, 'conda-meta')):
                from .exceptions import EnvironmentLocationNotFound
                raise EnvironmentLocationNotFound(prefix)
        elif re.search(r'\\|/', name_or_prefix):
            prefix = name_or_prefix
            if not isdir(join(prefix, 'conda-meta')):
                from .exceptions import EnvironmentLocationNotFound
                raise EnvironmentLocationNotFound(prefix)
        else:
            from .base.context import locate_prefix_by_name
            prefix = locate_prefix_by_name(self.context, name_or_prefix)

        # query environment
        old_conda_shlvl = int(os.getenv('CONDA_SHLVL', 0))
        old_conda_prefix = os.getenv('CONDA_PREFIX')

        if old_conda_prefix == prefix:
            return self.build_reactivate()
        elif old_conda_shlvl == 2 and os.getenv('CONDA_PREFIX_1') == prefix:
            return self.build_deactivate()

        activate_scripts = glob(join(
            prefix, 'etc', 'conda', 'activate.d', '*' + self.script_extension
        ))
        conda_default_env = self._default_env(prefix)
        conda_prompt_modifier = self._prompt_modifier(conda_default_env)

        if old_conda_shlvl == 0:
            new_path = self.pathsep_join(self._add_prefix_to_path(prefix))
            set_vars = {
                'CONDA_PYTHON_EXE': sys.executable,
                'PATH': new_path,
                'CONDA_PREFIX': prefix,
                'CONDA_SHLVL': old_conda_shlvl + 1,
                'CONDA_DEFAULT_ENV': conda_default_env,
                'CONDA_PROMPT_MODIFIER': conda_prompt_modifier,
            }
            deactivate_scripts = ()
        elif old_conda_shlvl == 1:
            new_path = self.pathsep_join(self._add_prefix_to_path(prefix))
            set_vars = {
                'PATH': new_path,
                'CONDA_PREFIX': prefix,
                'CONDA_PREFIX_%d' % old_conda_shlvl: old_conda_prefix,
                'CONDA_SHLVL': old_conda_shlvl + 1,
                'CONDA_DEFAULT_ENV': conda_default_env,
                'CONDA_PROMPT_MODIFIER': conda_prompt_modifier,
            }
            deactivate_scripts = ()
        elif old_conda_shlvl == 2:
            new_path = self.pathsep_join(self._replace_prefix_in_path(old_conda_prefix, prefix))
            set_vars = {
                'PATH': new_path,
                'CONDA_PREFIX': prefix,
                'CONDA_DEFAULT_ENV': conda_default_env,
                'CONDA_PROMPT_MODIFIER': conda_prompt_modifier,
            }
            deactivate_scripts = glob(join(
                old_conda_prefix, 'etc', 'conda', 'deactivate.d', '*' + self.script_extension
            ))
        else:
            raise NotImplementedError()

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
        elif old_conda_shlvl == 2:
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
        else:
            raise NotImplementedError()

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
        return glob(join(
            prefix, 'etc', 'conda', 'activate.d', '*' + self.script_extension
        ))

    def _get_deactivate_scripts(self, prefix):
        return glob(join(
            prefix, 'etc', 'conda', 'deactivate.d', '*' + self.script_extension
        ))


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
        return paths[0] if len(paths) == 1 else paths
    from subprocess import PIPE, Popen
    from shlex import split
    command = 'cygpath --path -f -'
    p = Popen(split(command), stdin=PIPE, stdout=PIPE, stderr=PIPE)
    joined = ensure_binary(("%s" % os.pathsep).join(paths))
    stdout, stderr = p.communicate(input=joined)
    rc = p.returncode
    if rc != 0 or stderr:
        from subprocess import CalledProcessError
        raise CalledProcessError(rc, command, "\n  stdout: %s\n  stderr: %s\n" % (stdout, stderr))
    if hasattr(stdout, 'decode'):
        stdout = stdout.decode('utf-8')
    final = stdout.strip().split(':')
    return final[0] if len(final) == 1 else tuple(final)


on_win = bool(sys.platform == "win32")
PY2 = sys.version_info[0] == 2
if PY2:  # pragma: py3 no cover
    string_types = basestring,  # NOQA

    def iteritems(d, **kw):
        return d.iteritems(**kw)
else:  # pragma: py2 no cover
    string_types = str,

    def iteritems(d, **kw):
        return iter(d.items(**kw))


def main():
    command = sys.argv[1]
    shell = sys.argv[2]
    activator = Activator(shell)
    remainder_args = sys.argv[3:] if len(sys.argv) >= 4 else ()
    # if '-h' in remainder_args or '--help' in remainder_args:
    #     pass
    if command == 'shell.activate':
        if len(remainder_args) > 1:
            from .exceptions import ArgumentError
            raise ArgumentError("activate only accepts a single argument")
        print(activator.activate(remainder_args and remainder_args[0] or "root"))
    elif command == 'shell.deactivate':
        if remainder_args:
            from .exceptions import ArgumentError
            raise ArgumentError("deactivate does not accept arguments")
        print(activator.deactivate())
    elif command == 'shell.reactivate':
        if remainder_args:
            from .exceptions import ArgumentError
            raise ArgumentError("reactivate does not accept arguments")
        print(activator.reactivate())
    else:
        raise NotImplementedError()
    return 0


if __name__ == '__main__':
    sys.exit(main())
