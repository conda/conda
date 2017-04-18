# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from glob import glob
import os
from os.path import abspath, basename, dirname, expanduser, expandvars, isdir, join
import re
import sys

try:
    from cytoolz.itertoolz import concatv
except ImportError:  # pragma: no cover
    from ._vendor.toolz.itertoolz import concatv  # NOQA

on_win = bool(sys.platform == "win32")
PY2 = sys.version_info[0] == 2
if PY2:  # pragma: py3 no cover
    def iteritems(d, **kw):
        return d.iteritems(**kw)
else:  # pragma: py2 no cover
    def iteritems(d, **kw):
        return iter(d.items(**kw))


def identity(x):
    return x


def expand(path):
    return abspath(expanduser(expandvars(path)))


def native_path_list_to_unix(path_value):
    if not on_win:
        return path_value
    from subprocess import PIPE, Popen
    from shlex import split
    command = "/usr/bin/env cygpath --path %s" % path_value
    p = Popen(split(command), stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    rc = p.returncode
    if rc != 0 or stderr:
        from subprocess import CalledProcessError
        raise CalledProcessError(rc, command, "\n  stdout: %s\n  stderr: %s\n" % (stdout, stderr))
    return stdout.strip()


class Activator(object):
    # Strategy is to use the Activator class, where all core logic is is build_activate()
    # or build_deactivate().  Each returns a map containing the keys: set_vars, unset_var,
    # activate_scripts, deactivate_scripts.

    def __init__(self, shell):
        from .base.context import context
        self.context = context

        if shell == 'posix':
            self.pathsep = os.pathsep
            self.path_conversion = native_path_list_to_unix
            self.script_extension = '.sh'

            self.unset_var_tmpl = 'unset %s'
            self.set_var_tmpl = 'export %s="%s"'
            self.run_script_tmpl = '. "%s"'

        else:
            raise NotImplementedError()

    def activate(self, name_or_prefix):
        return '\n'.join(self._make_commands(self.build_activate(name_or_prefix)))

    def deactivate(self):
        return '\n'.join(self._make_commands(self.build_deactivate()))

    def reactivate(self):
        return '\n'.join(self._make_commands(self.build_reactivate()))

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
        old_path = os.environ['PATH']

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
            new_path = self.path_conversion(self._add_prefix_to_path(old_path, prefix))
            set_vars = {
                'CONDA_PYTHON_PATH': sys.executable,
                'PATH': new_path,
                'CONDA_PREFIX': prefix,
                'CONDA_SHLVL': old_conda_shlvl + 1,
                'CONDA_DEFAULT_ENV': conda_default_env,
                'CONDA_PROMPT_MODIFIER': conda_prompt_modifier,
            }
            deactivate_scripts = ()
        elif old_conda_shlvl == 1:
            new_path = self.path_conversion(self._add_prefix_to_path(old_path, prefix))
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
            new_path = self.path_conversion(
                self._replace_prefix_in_path(old_path, old_conda_prefix, prefix)
            )
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
        old_path = os.environ['PATH']
        old_conda_prefix = os.environ['CONDA_PREFIX']
        deactivate_scripts = self._get_deactivate_scripts(old_conda_prefix)

        new_conda_shlvl = old_conda_shlvl - 1
        new_path = self.path_conversion(self._remove_prefix_from_path(old_path, old_conda_prefix))

        if old_conda_shlvl == 1:
            # TODO: warn conda floor
            unset_vars = (
                'CONDA_PREFIX',
                'CONDA_DEFAULT_ENV',
                'CONDA_PYTHON_PATH',
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

    def _get_path_dirs(self, prefix):
        if on_win:
            yield prefix.rstrip("\\")
            yield join(prefix, 'Library', 'mingw-w64', 'bin')
            yield join(prefix, 'Library', 'usr', 'bin')
            yield join(prefix, 'Library', 'bin')
            yield join(prefix, 'Scripts')
        else:
            yield join(prefix, 'bin')

    def _add_prefix_to_path(self, old_path, prefix):
        return self.pathsep.join(concatv(
            self._get_path_dirs(prefix),
            (old_path,),
        ))

    def _remove_prefix_from_path(self, current_path, prefix):
        _prefix_paths = (re.escape(self.pathsep.join(self._get_path_dirs(prefix)))
                         + r'%s?' % re.escape(self.pathsep))
        return re.sub(_prefix_paths, r'', current_path, 1)

    def _replace_prefix_in_path(self, current_path, old_prefix, new_prefix):
        old_prefix_paths = self.pathsep.join(self._get_path_dirs(old_prefix))
        if old_prefix_paths in current_path:
            new_prefix_paths = self.pathsep.join(self._get_path_dirs(new_prefix))
            return re.sub(re.escape(old_prefix_paths), new_prefix_paths, current_path, 1)
        else:
            return self._add_prefix_to_path(current_path, new_prefix)

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

    def _make_commands(self, cmds_dict):
        for key in cmds_dict.get('unset_vars', ()):
            yield self.unset_var_tmpl % key

        for key, value in iteritems(cmds_dict.get('set_vars', {})):
            yield self.set_var_tmpl % (key, value)

        for script in cmds_dict.get('deactivate_scripts', ()):
            yield self.run_script_tmpl % script

        for script in cmds_dict.get('activate_scripts', ()):
            yield self.run_script_tmpl % script


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
    main()
