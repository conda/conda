# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import OrderedDict
from errno import ENOENT
from itertools import chain
import json
import os
from os.path import abspath, basename, dirname, expanduser, expandvars, isdir, join, exists
import re
import sys
from textwrap import dedent

# Since we have to have configuration context here, anything imported by
#   conda.base.context is fair game, but nothing more.
from . import CONDA_PACKAGE_ROOT, CONDA_SOURCE_ROOT, CondaError
from ._vendor.toolz import concatv, drop
from .auxlib.compat import Utf8NamedTemporaryFile
from .base.constants import PREFIX_STATE_FILE, PACKAGE_ENV_VARS_DIR, CONDA_ENV_VARS_UNSET_VAR
from .base.context import ROOT_ENV_NAME, context, locate_prefix_by_name
from .common.compat import (FILESYSTEM_ENCODING, PY2, iteritems, on_win,
                            scandir, string_types, text_type)
from .common.path import paths_equal


class _Activator(object):
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

    # The following instance variables must be defined by each implementation.
    pathsep_join = None
    sep = None
    path_conversion = None
    script_extension = None
    tempfile_extension = None  # None means write instructions to stdout rather than a temp file
    command_join = None

    unset_var_tmpl = None
    export_var_tmpl = None
    set_var_tmpl = None
    run_script_tmpl = None

    hook_source_path = None

    def __init__(self, arguments=None):
        self._raw_arguments = arguments

        if PY2:
            self.environ = {ensure_fs_path_encoding(k): ensure_fs_path_encoding(v)
                            for k, v in iteritems(os.environ)}
        else:
            self.environ = os.environ.copy()

    # Once Python2 dies odargs can become kwargs again since dicts are ordered since 3.6.
    def get_export_unset_vars(self, odargs):
        """
        :param kwargs: environment variables to export. The `conda_exe_vars` meta
                       variables are also exported by default. If you do not want
                       this to happen then pass:
                           conda_exe_vars=None
                       .. if you pass and set any other variable to None, then it
                       emits it to the dict with a value of None.

        :return: A OrderedDict of env vars to export ordered the same way as kwargs.
                 And a list of env vars to unset.
        """
        kwargs = odargs
        conda_exe_vars_None = False if ('conda_exe_vars' not in kwargs or
                                        kwargs['conda_exe_vars'] is not None) else True
        conda_exe_unset_vars = []
        unset_vars = []
        # conda_exe_vars = context.conda_exe_vars_dict.copy()
        from collections import OrderedDict
        conda_exe_vars_export = OrderedDict()
        for k, v in context.conda_exe_vars_dict.items():
            if v is None or conda_exe_vars_None:
                conda_exe_unset_vars.append(k)
            else:
                conda_exe_vars_export[k] = self.path_conversion(v) if v else v
        from collections import OrderedDict
        export_vars = OrderedDict()
        for k, v in kwargs.items():
            if k == 'conda_exe_vars':
                continue
            elif v is None:
                unset_vars.append(k.upper())
            else:
                export_vars[k.upper()] = v
        # Just to make writing tests a bit more ergonomic we add these to the end.
        unset_vars += conda_exe_unset_vars
        export_vars = OrderedDict(chain(export_vars.items(), conda_exe_vars_export.items()))
        return export_vars, unset_vars

    # Used in tests only.
    def add_export_unset_vars(self, export_vars, unset_vars, **kwargs):
        new_export_vars, new_unset_vars = self.get_export_unset_vars(odargs=OrderedDict(kwargs))
        if export_vars is not None:
            export_vars = OrderedDict(chain(export_vars.items(), new_export_vars.items()))
        if unset_vars is not None:
            unset_vars += new_unset_vars
        return export_vars, unset_vars

    # Used in tests only.
    def get_scripts_export_unset_vars(self, **kwargs):
        export_vars, unset_vars = self.get_export_unset_vars(odargs=OrderedDict(kwargs))
        script_export_vars = script_unset_vars = None
        if export_vars:
            script_export_vars = self.command_join.join(
                [self.export_var_tmpl % (k, v) for k, v in export_vars.items()])
        if unset_vars:
            script_unset_vars = self.command_join.join(
                [self.unset_var_tmpl % (k) for k in unset_vars])
        return script_export_vars or '', script_unset_vars or ''

    def _finalize(self, commands, ext):
        commands = concatv(commands, ('',))  # add terminating newline
        if ext is None:
            return self.command_join.join(commands)
        elif ext:
            with Utf8NamedTemporaryFile('w+', suffix=ext, delete=False) as tf:
                # the default mode is 'w+b', and universal new lines don't work in that mode
                # command_join should account for that
                tf.write(self.command_join.join(commands))
            return tf.name
        else:
            raise NotImplementedError()

    def activate(self):
        if self.stack:
            builder_result = self.build_stack(self.env_name_or_prefix)
        else:
            builder_result = self.build_activate(self.env_name_or_prefix)
        return self._finalize(self._yield_commands(builder_result), self.tempfile_extension)

    def deactivate(self):
        return self._finalize(self._yield_commands(self.build_deactivate()),
                              self.tempfile_extension)

    def reactivate(self):
        return self._finalize(self._yield_commands(self.build_reactivate()),
                              self.tempfile_extension)

    def hook(self, auto_activate_base=None):
        builder = []
        builder.append(self._hook_preamble())
        with open(self.hook_source_path) as fsrc:
            builder.append(fsrc.read())
        if auto_activate_base is None and context.auto_activate_base or auto_activate_base:
            builder.append("conda activate base\n")
        postamble = self._hook_postamble()
        if postamble is not None:
            builder.append(postamble)
        return "\n".join(builder)

    def execute(self):
        # return value meant to be written to stdout
        self._parse_and_set_args(self._raw_arguments)
        return getattr(self, self.command)()

    def commands(self):
        """
        Returns a list of possible subcommands that are valid
        immediately following `conda` at the command line.
        This method is generally only used by tab-completion.
        """
        # Import locally to reduce impact on initialization time.
        from .cli.find_commands import find_commands
        from .cli.conda_argparse import generate_parser, find_builtin_commands
        # return value meant to be written to stdout
        # Hidden commands to provide metadata to shells.
        return "\n".join(sorted(
            find_builtin_commands(generate_parser()) +
            tuple(find_commands(True))
        ))

    def _hook_preamble(self):
        # must be implemented in subclass
        raise NotImplementedError()

    def _hook_postamble(self):
        return None

    def _parse_and_set_args(self, arguments):

        def raise_invalid_command_error(actual_command=None):
            from .exceptions import ArgumentError
            message = "'activate', 'deactivate', 'hook', 'commands', or 'reactivate' " \
                "command must be given"
            if actual_command:
                message += ". Instead got '%s'." % actual_command
            raise ArgumentError(message)

        if arguments is None or len(arguments) < 1:
            raise_invalid_command_error()

        command = arguments[0]
        arguments = tuple(drop(1, arguments))
        help_flags = ('-h', '--help', '/?')
        non_help_args = tuple(arg for arg in arguments if arg not in help_flags)
        help_requested = len(arguments) != len(non_help_args)
        remainder_args = list(arg for arg in non_help_args if arg and arg != command)

        if not command:
            raise_invalid_command_error()
        elif help_requested:
            from .exceptions import ActivateHelp, DeactivateHelp, GenericHelp
            help_classes = {
                'activate': ActivateHelp(),
                'deactivate': DeactivateHelp(),
                'hook': GenericHelp('hook'),
                'commands': GenericHelp('commands'),
                'reactivate': GenericHelp('reactivate'),
            }
            raise help_classes[command]
        elif command not in ('activate', 'deactivate', 'reactivate', 'hook', 'commands'):
            raise_invalid_command_error(actual_command=command)

        if command.endswith('activate') or command == 'hook':
            try:
                dev_idx = remainder_args.index('--dev')
            except ValueError:
                context.dev = False
            else:
                del remainder_args[dev_idx]
                context.dev = True

        if command == 'activate':
            self.stack = context.auto_stack and context.shlvl <= context.auto_stack
            try:
                stack_idx = remainder_args.index('--stack')
            except ValueError:
                stack_idx = -1
            try:
                no_stack_idx = remainder_args.index('--no-stack')
            except ValueError:
                no_stack_idx = -1
            if stack_idx >= 0 and no_stack_idx >= 0:
                from .exceptions import ArgumentError
                raise ArgumentError('cannot specify both --stack and --no-stack to ' + command)
            if stack_idx >= 0:
                self.stack = True
                del remainder_args[stack_idx]
            if no_stack_idx >= 0:
                self.stack = False
                del remainder_args[no_stack_idx]
            if len(remainder_args) > 1:
                from .exceptions import ArgumentError
                raise ArgumentError(command + ' does not accept more than one argument:\n'
                                    + str(remainder_args) + '\n')
            self.env_name_or_prefix = remainder_args and remainder_args[0] or 'base'

        else:
            if remainder_args:
                from .exceptions import ArgumentError
                raise ArgumentError('%s does not accept arguments\nremainder_args: %s\n'
                                    % (command, remainder_args))

        self.command = command

    def _yield_commands(self, cmds_dict):
        for key, value in sorted(iteritems(cmds_dict.get('export_path', {}))):
            yield self.export_var_tmpl % (key, value)

        for script in cmds_dict.get('deactivate_scripts', ()):
            yield self.run_script_tmpl % script

        for key in cmds_dict.get('unset_vars', ()):
            yield self.unset_var_tmpl % key

        for key, value in iteritems(cmds_dict.get('set_vars', {})):
            yield self.set_var_tmpl % (key, value)

        for key, value in iteritems(cmds_dict.get('export_vars', {})):
            yield self.export_var_tmpl % (key, value)

        for script in cmds_dict.get('activate_scripts', ()):
            yield self.run_script_tmpl % script

    def build_activate(self, env_name_or_prefix):
        return self._build_activate_stack(env_name_or_prefix, False)

    def build_stack(self, env_name_or_prefix):
        return self._build_activate_stack(env_name_or_prefix, True)

    def _build_activate_stack(self, env_name_or_prefix, stack):
        if re.search(r'\\|/', env_name_or_prefix):
            prefix = expand(env_name_or_prefix)
            if not isdir(join(prefix, 'conda-meta')):
                from .exceptions import EnvironmentLocationNotFound
                raise EnvironmentLocationNotFound(prefix)
        elif env_name_or_prefix in (ROOT_ENV_NAME, 'root'):
            prefix = context.root_prefix
        else:
            prefix = locate_prefix_by_name(env_name_or_prefix)

        # query environment
        old_conda_shlvl = int(self.environ.get('CONDA_SHLVL', '').strip() or 0)
        new_conda_shlvl = old_conda_shlvl + 1
        old_conda_prefix = self.environ.get('CONDA_PREFIX')

        if old_conda_prefix == prefix and old_conda_shlvl > 0:
            return self.build_reactivate()

        activate_scripts = self._get_activate_scripts(prefix)
        conda_default_env = self._default_env(prefix)
        conda_prompt_modifier = self._prompt_modifier(prefix, conda_default_env)
        conda_environment_env_vars = self._get_environment_env_vars(prefix)
        unset_env_vars = [k for k, v in conda_environment_env_vars.items()
                          if v == CONDA_ENV_VARS_UNSET_VAR]
        [conda_environment_env_vars.pop(_) for _ in unset_env_vars]

        clobbering_env_vars = [k for k in conda_environment_env_vars.keys()
                               if k in os.environ.keys()]

        for cvar in clobbering_env_vars:
            save_var = "__CONDA_SHLVL_%s_%s" % (old_conda_shlvl, cvar)
            conda_environment_env_vars[save_var] = os.environ.get(cvar)

        if clobbering_env_vars:
            print("WARNING: overwriting environment variables set in the machine", file=sys.stderr)
            print("overwriting variable %s" % ' '.join(clobbering_env_vars), file=sys.stderr)

        unset_vars = []
        if old_conda_shlvl == 0:
            new_path = self.pathsep_join(self._add_prefix_to_path(prefix))
            env_vars_to_export = OrderedDict((
                    ('path', new_path),
                    ('conda_prefix', prefix),
                    ('conda_shlvl', new_conda_shlvl),
                    ('conda_default_env', conda_default_env),
                    ('conda_prompt_modifier', conda_prompt_modifier)))
            for k, v in conda_environment_env_vars.items():
                env_vars_to_export[k] = v
            export_vars, unset_vars = self.get_export_unset_vars(odargs=env_vars_to_export)
            deactivate_scripts = ()
        else:
            if self.environ.get('CONDA_PREFIX_%s' % (old_conda_shlvl - 1)) == prefix:
                # in this case, user is attempting to activate the previous environment,
                #  i.e. step back down
                return self.build_deactivate()
            if stack:
                new_path = self.pathsep_join(self._add_prefix_to_path(prefix))
                deactivate_scripts = ()
                env_vars_to_export = OrderedDict((
                    ('path', new_path),
                    ('conda_prefix', prefix),
                    ('conda_shlvl', new_conda_shlvl),
                    ('conda_default_env', conda_default_env),
                    ('conda_prompt_modifier', conda_prompt_modifier)))
                for k, v in conda_environment_env_vars.items():
                    env_vars_to_export[k] = v
                export_vars, unset_vars = self.get_export_unset_vars(odargs=env_vars_to_export)
                export_vars['CONDA_PREFIX_%d' % old_conda_shlvl] = old_conda_prefix
                export_vars['CONDA_STACKED_%d' % new_conda_shlvl] = 'true'
            else:
                new_path = self.pathsep_join(
                    self._replace_prefix_in_path(old_conda_prefix, prefix))
                deactivate_scripts = self._get_deactivate_scripts(old_conda_prefix)
                env_vars_to_export = OrderedDict((
                    ('path', new_path),
                    ('conda_prefix', prefix),
                    ('conda_shlvl', new_conda_shlvl),
                    ('conda_default_env', conda_default_env),
                    ('conda_prompt_modifier', conda_prompt_modifier)))
                for k, v in conda_environment_env_vars.items():
                    env_vars_to_export[k] = v
                export_vars, unset_vars = self.get_export_unset_vars(odargs=env_vars_to_export)
                export_vars['CONDA_PREFIX_%d' % old_conda_shlvl] = old_conda_prefix

        set_vars = {}
        if context.changeps1:
            self._update_prompt(set_vars, conda_prompt_modifier)

        self._build_activate_shell_custom(export_vars)

        return {
            'unset_vars': unset_vars,
            'set_vars': set_vars,
            'export_vars': export_vars,
            'deactivate_scripts': deactivate_scripts,
            'activate_scripts': activate_scripts,
        }

    def build_deactivate(self):
        self._deactivate = True
        # query environment
        old_conda_prefix = self.environ.get('CONDA_PREFIX')
        old_conda_shlvl = int(self.environ.get('CONDA_SHLVL', '').strip() or 0)
        if not old_conda_prefix or old_conda_shlvl < 1:
            # no active environment, so cannot deactivate; do nothing
            return {
                'unset_vars': (),
                'set_vars': OrderedDict(),
                'export_vars': OrderedDict(),
                'deactivate_scripts': (),
                'activate_scripts': (),
            }
        deactivate_scripts = self._get_deactivate_scripts(old_conda_prefix)
        old_conda_environment_env_vars = self._get_environment_env_vars(old_conda_prefix)

        new_conda_shlvl = old_conda_shlvl - 1
        set_vars = {}
        if old_conda_shlvl == 1:
            new_path = self.pathsep_join(self._remove_prefix_from_path(old_conda_prefix))
            # You might think that you can remove the CONDA_EXE vars by passing conda_exe_vars=None
            # here so that "deactivate means deactivate" but you cannot since the conda shell
            # scripts still refer to them and they only set them once at the top. We could change
            # that though, the conda() shell function could set them instead of doing it at the
            # top.  This would be *much* cleaner. I personally cannot abide that I have
            # deactivated conda and anything at all in my env still references it (apart from the
            # shell script, we need something I suppose!)
            export_vars, unset_vars = self.get_export_unset_vars(odargs=OrderedDict((
                ('conda_prefix', None),
                ('conda_shlvl', new_conda_shlvl),
                ('conda_default_env', None),
                ('conda_prompt_modifier', None))))
            conda_prompt_modifier = ''
            activate_scripts = ()
            export_path = {'PATH': new_path, }
        else:
            assert old_conda_shlvl > 1
            new_prefix = self.environ.get('CONDA_PREFIX_%d' % new_conda_shlvl)
            conda_default_env = self._default_env(new_prefix)
            conda_prompt_modifier = self._prompt_modifier(new_prefix, conda_default_env)
            new_conda_environment_env_vars = self._get_environment_env_vars(new_prefix)

            old_prefix_stacked = 'CONDA_STACKED_%d' % old_conda_shlvl in self.environ
            new_path = ''

            unset_vars = ['CONDA_PREFIX_%d' % new_conda_shlvl]
            if old_prefix_stacked:
                new_path = self.pathsep_join(self._remove_prefix_from_path(old_conda_prefix))
                unset_vars.append('CONDA_STACKED_%d' % old_conda_shlvl)
            else:
                new_path = self.pathsep_join(
                    self._replace_prefix_in_path(old_conda_prefix, new_prefix)
                )

            env_vars_to_export = OrderedDict((
                ('conda_prefix', new_prefix),
                ('conda_shlvl', new_conda_shlvl),
                ('conda_default_env', conda_default_env),
                ('conda_prompt_modifier', conda_prompt_modifier)))
            for k, v in new_conda_environment_env_vars.items():
                env_vars_to_export[k] = v
            export_vars, unset_vars2 = self.get_export_unset_vars(odargs=env_vars_to_export)
            unset_vars += unset_vars2
            export_path = {'PATH': new_path, }
            activate_scripts = self._get_activate_scripts(new_prefix)

        if context.changeps1:
            self._update_prompt(set_vars, conda_prompt_modifier)

        for env_var in old_conda_environment_env_vars.keys():
            unset_vars.append(env_var)
            save_var = "__CONDA_SHLVL_%s_%s" % (new_conda_shlvl, env_var)
            if save_var in os.environ.keys():
                export_vars[env_var] = os.environ[save_var]
        return {
            'unset_vars': unset_vars,
            'set_vars': set_vars,
            'export_vars': export_vars,
            'export_path': export_path,
            'deactivate_scripts': deactivate_scripts,
            'activate_scripts': activate_scripts,
        }

    def build_reactivate(self):
        self._reactivate = True
        conda_prefix = self.environ.get('CONDA_PREFIX')
        conda_shlvl = int(self.environ.get('CONDA_SHLVL', '').strip() or 0)
        if not conda_prefix or conda_shlvl < 1:
            # no active environment, so cannot reactivate; do nothing
            return {
                'unset_vars': (),
                'set_vars': OrderedDict(),
                'export_vars': OrderedDict(),
                'deactivate_scripts': (),
                'activate_scripts': (),
            }
        conda_default_env = self.environ.get('CONDA_DEFAULT_ENV', self._default_env(conda_prefix))
        new_path = self.pathsep_join(self._replace_prefix_in_path(conda_prefix, conda_prefix))
        set_vars = {}
        conda_prompt_modifier = self._prompt_modifier(conda_prefix, conda_default_env)
        if context.changeps1:
            self._update_prompt(set_vars, conda_prompt_modifier)

        env_vars_to_unset = ()
        env_vars_to_export = OrderedDict([
            ('PATH', new_path),
            ('CONDA_SHLVL', conda_shlvl),
            ('CONDA_PROMPT_MODIFIER', self._prompt_modifier(conda_prefix, conda_default_env)),
        ])
        conda_environment_env_vars = self._get_environment_env_vars(conda_prefix)
        for k, v in conda_environment_env_vars.items():
            if v == CONDA_ENV_VARS_UNSET_VAR:
                env_vars_to_unset = env_vars_to_unset + (k,)
            else:
                env_vars_to_export[k] = v
        # environment variables are set only to aid transition from conda 4.3 to conda 4.4
        return {
            'unset_vars': env_vars_to_unset,
            'set_vars': set_vars,
            'export_vars': env_vars_to_export,
            'deactivate_scripts': self._get_deactivate_scripts(conda_prefix),
            'activate_scripts': self._get_activate_scripts(conda_prefix),
        }

    def _get_starting_path_list(self):
        # For isolation, running the conda test suite *without* env. var. inheritance
        # every so often is a good idea. We should probably make this a pytest fixture
        # along with one that tests both hardlink-only and copy-only, but before that
        # conda's testsuite needs to be a lot faster!
        clean_paths = {'darwin': '/usr/bin:/bin:/usr/sbin:/sbin',
                       # You may think 'let us do something more clever here and interpolate
                       # `%windir%`' but the point here is the the whole env. is cleaned out
                       'win32': 'C:\\Windows\\system32;'
                                'C:\\Windows;'
                                'C:\\Windows\\System32\\Wbem;'
                                'C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\'
                       }
        path = self.environ.get('PATH',
                                clean_paths[sys.platform] if sys.platform in clean_paths else
                                '/usr/bin')
        path_split = path.split(os.pathsep)
        # We used to prepend sys.prefix\Library\bin to PATH on startup but not anymore.
        # Instead, in conda 4.6 we add the full suite of entries. This is performed in
        # condabin\conda.bat and condabin\ _conda_activate.bat. However, we
        # need to ignore the stuff we add there, and only consider actual PATH entries.
        prefix_dirs = tuple(self._get_path_dirs(sys.prefix))
        start_index = 0
        while (start_index < len(prefix_dirs) and
               start_index < len(path_split) and
               paths_equal(path_split[start_index], prefix_dirs[start_index])):
            start_index += 1
        path_split = path_split[start_index:]
        library_bin_dir = self.path_conversion(
                self.sep.join((sys.prefix, 'Library', 'bin')))
        if paths_equal(path_split[0], library_bin_dir):
            path_split = path_split[1:]
        return path_split

    def _get_path_dirs(self, prefix, extra_library_bin=False):
        if on_win:  # pragma: unix no cover
            yield prefix.rstrip("\\")
            yield self.sep.join((prefix, 'Library', 'mingw-w64', 'bin'))
            yield self.sep.join((prefix, 'Library', 'usr', 'bin'))
            yield self.sep.join((prefix, 'Library', 'bin'))
            yield self.sep.join((prefix, 'Scripts'))
            yield self.sep.join((prefix, 'bin'))
        else:
            yield self.sep.join((prefix, 'bin'))

    def _add_prefix_to_path(self, prefix, starting_path_dirs=None):
        prefix = self.path_conversion(prefix)
        if starting_path_dirs is None:
            path_list = list(self.path_conversion(self._get_starting_path_list()))
        else:
            path_list = list(self.path_conversion(starting_path_dirs))

        # If this is the first time we're activating an environment, we need to ensure that
        # the condabin directory is included in the path list.
        # Under normal conditions, if the shell hook is working correctly, this should
        # never trigger.
        old_conda_shlvl = int(self.environ.get('CONDA_SHLVL', '').strip() or 0)
        if not old_conda_shlvl and not any(p.endswith("condabin") for p in path_list):
            condabin_dir = self.path_conversion(join(context.conda_prefix, "condabin"))
            path_list.insert(0, condabin_dir)

        path_list[0:0] = list(self.path_conversion(self._get_path_dirs(prefix)))
        return tuple(path_list)

    def _remove_prefix_from_path(self, prefix, starting_path_dirs=None):
        return self._replace_prefix_in_path(prefix, None, starting_path_dirs)

    def _replace_prefix_in_path(self, old_prefix, new_prefix, starting_path_dirs=None):
        old_prefix = self.path_conversion(old_prefix)
        new_prefix = self.path_conversion(new_prefix)
        if starting_path_dirs is None:
            path_list = list(self.path_conversion(self._get_starting_path_list()))
        else:
            path_list = list(self.path_conversion(starting_path_dirs))

        def index_of_path(paths, test_path):
            for q, path in enumerate(paths):
                if paths_equal(path, test_path):
                    return q
            return None

        if old_prefix is not None:
            prefix_dirs = tuple(self._get_path_dirs(old_prefix))
            first_idx = index_of_path(path_list, prefix_dirs[0])
            if first_idx is None:
                first_idx = 0
            else:
                prefix_dirs_idx = len(prefix_dirs) - 1
                last_idx = None
                while last_idx is None and prefix_dirs_idx > -1:
                    last_idx = index_of_path(path_list, prefix_dirs[prefix_dirs_idx])
                    if last_idx is None:
                        print(
                            "Did not find path entry {0}".format(prefix_dirs[prefix_dirs_idx]),
                            file=sys.stderr
                        )
                    prefix_dirs_idx = prefix_dirs_idx - 1
                # this compensates for an extra Library/bin dir entry from the interpreter on
                #     windows.  If that entry isn't being added, it should have no effect.
                library_bin_dir = self.path_conversion(
                    self.sep.join((sys.prefix, 'Library', 'bin')))
                if path_list[last_idx + 1] == library_bin_dir:
                    last_idx += 1
                del path_list[first_idx:last_idx + 1]
        else:
            first_idx = 0

        if new_prefix is not None:
            path_list[first_idx:first_idx] = list(self._get_path_dirs(new_prefix))

        return tuple(path_list)

    def _build_activate_shell_custom(self, export_vars):
        # A method that can be overriden by shell-specific implementations.
        # The signature of this method may change in the future.
        pass

    def _update_prompt(self, set_vars, conda_prompt_modifier):
        pass

    def _default_env(self, prefix):
        if paths_equal(prefix, context.root_prefix):
            return 'base'
        return basename(prefix) if basename(dirname(prefix)) == 'envs' else prefix

    def _prompt_modifier(self, prefix, conda_default_env):
        if context.changeps1:
            # Get current environment and prompt stack
            env_stack = []
            prompt_stack = []
            old_shlvl = int(self.environ.get('CONDA_SHLVL', '0').rstrip())
            for i in range(1, old_shlvl+1):
                if i == old_shlvl:
                    env_i = self._default_env(self.environ.get('CONDA_PREFIX', ''))
                else:
                    env_i = self._default_env(
                            self.environ.get('CONDA_PREFIX_{}'.format(i), '').rstrip())
                stacked_i = bool(self.environ.get('CONDA_STACKED_{}'.format(i), '').rstrip())
                env_stack.append(env_i)
                if not stacked_i:
                    prompt_stack = prompt_stack[0:-1]
                prompt_stack.append(env_i)

            # Modify prompt stack according to pending operation
            deactivate = getattr(self, '_deactivate', False)
            reactivate = getattr(self, '_reactivate', False)
            if deactivate:
                prompt_stack = prompt_stack[0:-1]
                env_stack = env_stack[0:-1]
                stacked = bool(self.environ.get('CONDA_STACKED_{}'.format(old_shlvl), '').rstrip())
                if not stacked and env_stack:
                    prompt_stack.append(env_stack[-1])
            elif reactivate:
                pass
            else:
                stack = getattr(self, 'stack', False)
                if not stack:
                    prompt_stack = prompt_stack[0:-1]
                prompt_stack.append(conda_default_env)

            conda_stacked_env = ','.join(prompt_stack[::-1])

            return context.env_prompt.format(
                default_env=conda_default_env,
                stacked_env=conda_stacked_env,
                prefix=prefix,
                name=basename(prefix),
            )
        else:
            return ""

    def _get_activate_scripts(self, prefix):
        _script_extension = self.script_extension
        se_len = -len(_script_extension)
        try:
            paths = (entry.path for entry in scandir(join(prefix, 'etc', 'conda', 'activate.d')))
        except EnvironmentError:
            return ()
        return self.path_conversion(sorted(
            p for p in paths if p[se_len:] == _script_extension
        ))

    def _get_deactivate_scripts(self, prefix):
        _script_extension = self.script_extension
        se_len = -len(_script_extension)
        try:
            paths = (entry.path for entry in scandir(join(prefix, 'etc', 'conda', 'deactivate.d')))
        except EnvironmentError:
            return ()
        return self.path_conversion(sorted(
            (p for p in paths if p[se_len:] == _script_extension),
            reverse=True
        ))

    def _get_environment_env_vars(self, prefix):
        env_vars_file = join(prefix, PREFIX_STATE_FILE)
        pkg_env_var_dir = join(prefix, PACKAGE_ENV_VARS_DIR)
        env_vars = OrderedDict()

        # First get env vars from packages
        if exists(pkg_env_var_dir):
            for pkg_env_var_path in sorted(entry.path for entry in scandir(pkg_env_var_dir)):
                with open(pkg_env_var_path, 'r') as f:
                    env_vars.update(json.loads(f.read(), object_pairs_hook=OrderedDict))

        # Then get env vars from environment specification
        if exists(env_vars_file):
            with open(env_vars_file, 'r') as f:
                prefix_state = json.loads(f.read(), object_pairs_hook=OrderedDict)
                prefix_state_env_vars = prefix_state.get('env_vars', {})
                dup_vars = [ev for ev in env_vars.keys() if ev in prefix_state_env_vars.keys()]
                for dup in dup_vars:
                    print("WARNING: duplicate env vars detected. Vars from the environment "
                          "will overwrite those from packages", file=sys.stderr)
                    print("variable %s duplicated" % dup, file=sys.stderr)
                env_vars.update(prefix_state_env_vars)

        return env_vars


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
    if paths is None:
        return None
    from subprocess import CalledProcessError, PIPE, Popen
    from conda.auxlib.compat import shlex_split_unicode
    # It is very easy to end up with a bash in one place and a cygpath in another due to e.g.
    # using upstream MSYS2 bash, but with a conda env that does not have bash but does have
    # cygpath.  When this happens, we have two different virtual POSIX machines, rooted at
    # different points in the Windows filesystem.  We do our path conversions with one and
    # expect the results to work with the other.  It does not.
    from .common.path import which
    bash = which('bash')
    command = os.path.join(dirname(bash), 'cygpath') if bash else 'cygpath'
    command += ' --path -f -'

    single_path = isinstance(paths, string_types)
    joined = paths if single_path else ("%s" % os.pathsep).join(paths)

    if hasattr(joined, 'encode'):
        joined = joined.encode('utf-8')

    try:
        p = Popen(shlex_split_unicode(command), stdin=PIPE, stdout=PIPE, stderr=PIPE)
    except EnvironmentError as e:
        if e.errno != ENOENT:
            raise
        # This code path should (hopefully) never be hit be real conda installs. It's here
        # as a backup for tests run under cmd.exe with cygpath not available.
        def _translation(found_path):  # NOQA
            found = found_path.group(1).replace("\\", "/").replace(":", "").replace("//", "/")
            return "/" + found.rstrip("/")
        joined = ensure_fs_path_encoding(joined)
        stdout = re.sub(
            r'([a-zA-Z]:[\/\\\\]+(?:[^:*?\"<>|;]+[\/\\\\]*)*)',
            _translation,
            joined
        ).replace(";/", ":/").rstrip(";")
    else:
        stdout, stderr = p.communicate(input=joined)
        rc = p.returncode
        if rc != 0 or stderr:
            message = "\n  stdout: %s\n  stderr: %s\n  rc: %s\n" % (stdout, stderr, rc)
            print(message, file=sys.stderr)
            raise CalledProcessError(rc, command, message)
        if hasattr(stdout, 'decode'):
            stdout = stdout.decode('utf-8')
        stdout = stdout.strip()
    final = stdout and stdout.split(':') or ()
    return final[0] if single_path else tuple(final)


def path_identity(paths):
    if isinstance(paths, string_types):
        return os.path.normpath(paths)
    elif paths is None:
        return None
    else:
        return tuple(os.path.normpath(_) for _ in paths)


class PosixActivator(_Activator):

    def __init__(self, arguments=None):
        self.pathsep_join = ':'.join
        self.sep = '/'
        self.path_conversion = native_path_to_unix
        self.script_extension = '.sh'
        self.tempfile_extension = None  # write instructions to stdout rather than a temp file
        self.command_join = '\n'

        self.unset_var_tmpl = 'unset %s'
        self.export_var_tmpl = "export %s='%s'"
        self.set_var_tmpl = "%s='%s'"
        self.run_script_tmpl = '. "%s"'

        self.hook_source_path = join(CONDA_PACKAGE_ROOT, 'shell', 'etc', 'profile.d', 'conda.sh')

        super(PosixActivator, self).__init__(arguments)

    def _update_prompt(self, set_vars, conda_prompt_modifier):
        ps1 = self.environ.get('PS1', '')
        if 'POWERLINE_COMMAND' in ps1:
            # Defer to powerline (https://github.com/powerline/powerline) if it's in use.
            return
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

    def _hook_preamble(self):
        result = ''
        for key, value in context.conda_exe_vars_dict.items():
            if value is None:
                # Using `unset_var_tmpl` would cause issues for people running
                # with shell flag -u set (error on unset).
                # result += join(self.unset_var_tmpl % key) + '\n'
                result += join(self.export_var_tmpl % (key, '')) + '\n'
            else:
                if key in ('PYTHONPATH', 'CONDA_EXE'):
                    result += join(self.export_var_tmpl % (
                        key, self.path_conversion(value))) + '\n'
                else:
                    result += join(self.export_var_tmpl % (key, value)) + '\n'
        return result


class CshActivator(_Activator):

    def __init__(self, arguments=None):
        self.pathsep_join = ':'.join
        self.sep = '/'
        self.path_conversion = native_path_to_unix
        self.script_extension = '.csh'
        self.tempfile_extension = None  # write instructions to stdout rather than a temp file
        self.command_join = ';\n'

        self.unset_var_tmpl = 'unsetenv %s'
        self.export_var_tmpl = 'setenv %s "%s"'
        self.set_var_tmpl = "set %s='%s'"
        self.run_script_tmpl = 'source "%s"'

        self.hook_source_path = join(CONDA_PACKAGE_ROOT, 'shell', 'etc', 'profile.d', 'conda.csh')

        super(CshActivator, self).__init__(arguments)

    def _update_prompt(self, set_vars, conda_prompt_modifier):
        prompt = self.environ.get('prompt', '')
        current_prompt_modifier = self.environ.get('CONDA_PROMPT_MODIFIER')
        if current_prompt_modifier:
            prompt = re.sub(re.escape(current_prompt_modifier), r'', prompt)
        set_vars.update({
            'prompt': conda_prompt_modifier + prompt,
        })

    def _hook_preamble(self):
        if on_win:
            return dedent(
                f"""
                setenv CONDA_EXE `cygpath {context.conda_exe}`
                setenv _CONDA_ROOT `cygpath {context.conda_prefix}`
                setenv _CONDA_EXE `cygpath {context.conda_exe}`
                setenv CONDA_PYTHON_EXE `cygpath {sys.executable}`
                """
            ).strip()
        else:
            return dedent(
                f"""
                setenv CONDA_EXE "{context.conda_exe}"
                setenv _CONDA_ROOT "{context.conda_prefix}"
                setenv _CONDA_EXE "{context.conda_exe}"
                setenv CONDA_PYTHON_EXE "{sys.executable}"
                """
            ).strip()


class XonshActivator(_Activator):

    @staticmethod
    def path_conversion(paths):
        if not on_win:
            return path_identity(paths)
        elif isinstance(paths, string_types):
            return paths.replace('\\', '/')
        elif paths is None:
            return None
        else:
            return tuple([path.replace('\\', '/') for path in paths])

    def __init__(self, arguments=None):
        self.pathsep_join = ';'.join if on_win else ':'.join
        self.sep = '/'
        self.tempfile_extension = None
        self.command_join = '\n'

        self.unset_var_tmpl = 'del $%s'
        self.export_var_tmpl = "$%s = '%s'"
        self.set_var_tmpl = "$%s = '%s'"  # TODO: determine if different than export_var_tmpl

        # 'scripts' really refer to de/activation scripts, not scripts in the language per se
        # xonsh can piggy-back activation scripts from other languages depending on the platform
        import platform
        if platform.system() == 'Windows':
            self.script_extension = '.bat'
            self.run_script_tmpl = 'source-cmd --suppress-skip-message "%s"'
        else:
            self.script_extension = '.sh'
            self.run_script_tmpl = 'source-bash --suppress-skip-message "%s"'

        self.hook_source_path = join(CONDA_PACKAGE_ROOT, 'shell', 'conda.xsh')

        super(XonshActivator, self).__init__(arguments)

    def _hook_preamble(self):
        return '$CONDA_EXE = "%s"' % self.path_conversion(context.conda_exe)


class CmdExeActivator(_Activator):

    def __init__(self, arguments=None):
        self.pathsep_join = ';'.join
        self.sep = '\\'
        self.path_conversion = path_identity
        self.script_extension = '.bat'
        self.tempfile_extension = '.bat'
        self.command_join = '\n'

        self.unset_var_tmpl = '@SET %s='
        self.export_var_tmpl = '@SET "%s=%s"'
        self.set_var_tmpl = '@SET "%s=%s"'  # TODO: determine if different than export_var_tmpl
        self.run_script_tmpl = '@CALL "%s"'

        self.hook_source_path = None
        # TODO: cmd.exe doesn't get a hook function? Or do we need to do something different?
        #       Like, for cmd.exe only, put a special directory containing only conda.bat on PATH?

        super(CmdExeActivator, self).__init__(arguments)

    # def _hook_preamble(self):
    #     if on_win:
    #         return '@chcp 65001'


class FishActivator(_Activator):

    def __init__(self, arguments=None):
        self.pathsep_join = '" "'.join
        self.sep = '/'
        self.path_conversion = native_path_to_unix
        self.script_extension = '.fish'
        self.tempfile_extension = None  # write instructions to stdout rather than a temp file
        self.command_join = ';\n'

        self.unset_var_tmpl = 'set -e %s'
        self.export_var_tmpl = 'set -gx %s "%s"'
        self.set_var_tmpl = 'set -g %s "%s"'
        self.run_script_tmpl = 'source "%s"'

        self.hook_source_path = join(CONDA_PACKAGE_ROOT, 'shell', 'etc', 'fish', 'conf.d',
                                     'conda.fish')

        super(FishActivator, self).__init__(arguments)

    def _hook_preamble(self):
        if on_win:
            return dedent(
                f"""
                set -gx CONDA_EXE (cygpath "{context.conda_exe}")
                set _CONDA_ROOT (cygpath "{context.conda_prefix}")
                set _CONDA_EXE (cygpath "{context.conda_exe}")
                set -gx CONDA_PYTHON_EXE (cygpath "{sys.executable}")
                """
            ).strip()
        else:
            return dedent(
                f"""
                set -gx CONDA_EXE "{context.conda_exe}"
                set _CONDA_ROOT "{context.conda_prefix}"
                set _CONDA_EXE "{context.conda_exe}"
                set -gx CONDA_PYTHON_EXE "{sys.executable}"
                """
            ).strip()


class PowerShellActivator(_Activator):

    def __init__(self, arguments=None):
        self.pathsep_join = ';'.join if on_win else ':'.join
        self.sep = '\\' if on_win else '/'
        self.path_conversion = path_identity
        self.script_extension = '.ps1'
        self.tempfile_extension = None  # write instructions to stdout rather than a temp file
        self.command_join = '\n'

        self.unset_var_tmpl = '$Env:%s = ""'
        self.export_var_tmpl = '$Env:%s = "%s"'
        self.set_var_tmpl = '$Env:%s = "%s"'
        self.run_script_tmpl = '. "%s"'

        self.hook_source_path = join(CONDA_PACKAGE_ROOT, 'shell', 'condabin', 'conda-hook.ps1')

        super(PowerShellActivator, self).__init__(arguments)

    def _hook_preamble(self):
        if context.dev:
            return dedent(
                f"""
                $Env:PYTHONPATH = "{CONDA_SOURCE_ROOT}"
                $Env:CONDA_EXE = "{sys.executable}"
                $Env:_CE_M = "-m"
                $Env:_CE_CONDA = "conda"
                $Env:_CONDA_ROOT = "{CONDA_PACKAGE_ROOT}"
                $Env:_CONDA_EXE = "{context.conda_exe}"
                $CondaModuleArgs = @{{ChangePs1 = ${context.changeps1}}}
                """
            ).strip()
        else:
            return dedent(
                f"""
                $Env:CONDA_EXE = "{context.conda_exe}"
                $Env:_CE_M = ""
                $Env:_CE_CONDA = ""
                $Env:_CONDA_ROOT = "{context.conda_prefix}"
                $Env:_CONDA_EXE = "{context.conda_exe}"
                $CondaModuleArgs = @{{ChangePs1 = ${context.changeps1}}}
                """
            ).strip()

    def _hook_postamble(self):
        return "Remove-Variable CondaModuleArgs"


class JSONFormatMixin(_Activator):
    """Returns the necessary values for activation as JSON, so that tools can use them."""

    def __init__(self, arguments=None):
        self.pathsep_join = list
        self.tempfile_extension = None  # write instructions to stdout rather than a temp file
        self.command_join = list

        super(JSONFormatMixin, self).__init__(arguments)

    def _hook_preamble(self):
        if context.dev:
            return {
                "PYTHONPATH": CONDA_SOURCE_ROOT,
                "CONDA_EXE": sys.executable,
                "_CE_M": "-m",
                "_CE_CONDA": "conda",
                "_CONDA_ROOT": CONDA_PACKAGE_ROOT,
                "_CONDA_EXE": context.conda_exe,
            }
        else:
            return {
                'CONDA_EXE': context.conda_exe,
                '_CE_M': '',
                '_CE_CONDA': '',
                '_CONDA_ROOT': context.conda_prefix,
                '_CONDA_EXE': context.conda_exe,
            }

    def get_scripts_export_unset_vars(self, **kwargs):
        export_vars, unset_vars = self.get_export_unset_vars(odargs=OrderedDict(kwargs))
        script_export_vars = script_unset_vars = None
        if export_vars:
            script_export_vars = dict(export_vars.items())
        if unset_vars:
            script_unset_vars = unset_vars
        return script_export_vars or {}, script_unset_vars or []

    def _finalize(self, commands, ext):
        merged = {}
        for _cmds in commands:
            merged.update(_cmds)

        commands = merged
        if ext is None:
            return json.dumps(commands, indent=2)
        elif ext:
            with Utf8NamedTemporaryFile('w+', suffix=ext, delete=False) as tf:
                # the default mode is 'w+b', and universal new lines don't work in that mode
                # command_join should account for that
                json.dump(commands, tf, indent=2)
            return tf.name
        else:
            raise NotImplementedError()

    def _yield_commands(self, cmds_dict):
        # TODO: _Is_ defining our own object shape here any better than
        # just dumping the `cmds_dict`?
        path = cmds_dict.get('export_path', {})
        export_vars = cmds_dict.get('export_vars', {})
        # treat PATH specially
        if 'PATH' in export_vars:
            new_path = path.get('PATH', [])
            new_path.extend(export_vars.pop('PATH'))
            path['PATH'] = new_path

        yield {
            'path': path,
            'vars': {
                'export': export_vars,
                'unset': cmds_dict.get('unset_vars', ()),
                'set': cmds_dict.get('set_vars', {}),
            },
            'scripts': {
                'activate': cmds_dict.get('activate_scripts', ()),
                'deactivate': cmds_dict.get('deactivate_scripts', ()),
            }
        }


activator_map = {
    'posix': PosixActivator,
    'ash': PosixActivator,
    'bash': PosixActivator,
    'dash': PosixActivator,
    'zsh': PosixActivator,
    'csh': CshActivator,
    'tcsh': CshActivator,
    'xonsh': XonshActivator,
    'cmd.exe': CmdExeActivator,
    'fish': FishActivator,
    'powershell': PowerShellActivator,
}

formatter_map = {
    'json': JSONFormatMixin,
}


def _build_activator_cls(shell):
    """Construct the activator class dynamically from a base activator and any
    number of formatters, appended using '+' to the name. For example,
    `posix+json` (as in `conda shell.posix+json activate`) would use the
    `PosixActivator` base class and add the `JSONFormatMixin`."""
    shell_etc = shell.split('+')
    activator, formatters = shell_etc[0], shell_etc[1:]
    bases = [activator_map[activator]]

    for f in formatters:
        bases.append(formatter_map[f])

    cls = type(str('Activator'), tuple(bases), {})
    return cls


def main(argv=None):
    from .common.compat import init_std_stream_encoding

    context.__init__()  # On import, context does not include SEARCH_PATH. This line fixes that.

    init_std_stream_encoding()
    argv = argv or sys.argv
    assert len(argv) >= 2
    assert argv[1].startswith('shell.')
    shell = argv[1].replace('shell.', '', 1)
    activator_args = argv[2:]
    try:
        activator_cls = _build_activator_cls(shell)
    except KeyError:
        raise CondaError("%s is not a supported shell." % shell)

    activator = activator_cls(activator_args)
    try:
        print(activator.execute(), end='')
        return 0
    except Exception as e:
        if isinstance(e, CondaError):
            print(text_type(e), file=sys.stderr)
            return e.return_code
        else:
            raise


if __name__ == '__main__':
    sys.exit(main())
