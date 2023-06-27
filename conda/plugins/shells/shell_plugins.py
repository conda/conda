# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import argparse
import json
import os
import re
import sys

from conda.activate import expand
from conda.base.constants import (
    CONDA_ENV_VARS_UNSET_VAR,
    PACKAGE_ENV_VARS_DIR,
    PREFIX_STATE_FILE,
)
from conda.base.context import ROOT_ENV_NAME, context, locate_prefix_by_name
from conda.common.compat import on_win
from conda.common.path import paths_equal
from conda.plugins.types import CondaShellPlugins


class PluginActivator:
    """
    Activate and deactivate have two tasks:
        1. Set and unset environment variables
        2. Execute/source activate.d/deactivate.d scripts

    Shells should also use 'reactivate' following conda's install, update, and
        remove/uninstall commands.

    All core logic is in build_activate() or build_deactivate(), and is independent of
    shell type.  Each returns a map containing the keys:
        export_vars
        unset_var
        activate_scripts
        deactivate_scripts

    Each shell plugin hook provides the shell-specific information needed to implement
    the methods of this class.
    """

    def __init__(self):
        """
        Create properties so that each class property is assigned the value from the corresponding
        property in the plugin hook's named tuple. If a property is missing from the plugin hook,
        it will be assigned a value of None.

        If no shell-compatible plugin is installed CondaPluginManager.get_shell_syntax() will
        raise an error, so none of the other methods will be run.

        Expected properties:
            self.name: str
            self.summary: str
            script_path: str
            self.pathsep_join: str
            self.sep: str
            self.path_conversion: Callable[
                [str | Iterable[str] | None], str | tuple[str, ...] | None
            ]
            self.script_extension: str
            self.tempfile_extension: str | None
            self.command_join: str
            self.run_script_tmpl: str
            self.environ: map
        """
        syntax = context.plugin_manager.get_shell_syntax()

        for field in CondaShellPlugins._fields:
            setattr(self, field, getattr(syntax, field, None))

        self.environ = os.environ.copy()

    def update_env_map(self, cmds_dict: dict) -> map:
        """
        Create an environment mapping for use with os.execve, based on the builder dictionary.
        """
        env_map = os.environ.copy()

        unset_vars = cmds_dict["unset_vars"]
        set_vars = cmds_dict["set_vars"]
        export_path = cmds_dict.get("export_path", {})
        export_vars = cmds_dict.get("export_vars", {})

        for key in unset_vars:
            env_map.pop(str(key), None)

        for key, value in set_vars.items():
            env_map[str(key)] = str(value)

        for key, value in export_path.items():
            env_map[str(key)] = str(value)

        for key, value in export_vars.items():
            env_map[str(key)] = str(value)

        return env_map

    def get_activate_builder(self) -> dict:
        """
        Create dictionary containing the environment variables to be set, unset and
        exported, as well as the package activation and deactivation scripts to be run.
        """
        if self.stack:
            builder_result = self._build_activate_stack(self.env_name_or_prefix, True)
        else:
            builder_result = self._build_activate_stack(self.env_name_or_prefix, False)
        return builder_result

    def parse_and_build(self, args: argparse.Namespace) -> dict:
        """
        Parse CLI arguments. Build and return the dictionary that contains environment variables
            to be set, unset, and exported, and any relevant package activation and deactivation
            scripts that should be run.
        Set context.dev if a --dev flag exists.
        For activate, set self.env_name_or_prefix and self.stack.
        """
        context.dev = args.dev or context.dev

        if args.command == "activate":
            self.env_name_or_prefix = args.env or "base"
            if args.stack is None:
                self.stack = context.auto_stack and context.shlvl <= context.auto_stack
            else:
                self.stack = args.stack
            cmds_dict = self.get_activate_builder()
        elif args.command == "deactivate":
            cmds_dict = self.build_deactivate()
        elif args.command == "reactivate":
            cmds_dict = self.build_reactivate()

        return cmds_dict

    def activate(self, cmds_dict: dict) -> SystemExit:
        """
        Change environment. As a new process in in new environment, run deactivate
        scripts from packages in old environment (to reset env variables) and
        activate scripts from packages installed in new environment.
        """
        path = self.script_path
        arg_list = [path]
        env_map = self.update_env_map(cmds_dict)

        deactivate_scripts = cmds_dict.get("deactivate_scripts", ())

        if deactivate_scripts:
            deactivate_list = [
                (self.run_script_tmpl % script) + self.command_join
                for script in deactivate_scripts
            ]
            arg_list.extend(deactivate_list)

        activate_scripts = cmds_dict.get("activate_scripts", ())

        if activate_scripts:
            activate_list = [
                (self.run_script_tmpl % script) + self.command_join
                for script in activate_scripts
            ]
            arg_list.extend(activate_list)

        os.execve(path, arg_list, env_map)

    # The logic of the following methods replicates the homologous methods in _Activator,
    # with the exception of removing logic supporting updates to the prompt.
    # Direct use of os.environ has been changed in favor of using a shallow copy.
    # Type hints and doc strings have been added where the originals were missing these.
    def get_export_unset_vars(
        self, export_metavars=True, **kwargs
    ) -> tuple(dict, list):
        """
        :param export_metavars: whether to export `conda_exe_vars` meta variables.
        :param kwargs: environment variables to export.
            .. if you pass and set any other variable to None, then it
            emits it to the dict with a value of None.

        :return: A dict of env vars to export ordered the same way as kwargs.
            And a list of env vars to unset.
        """
        unset_vars = []
        export_vars = {}

        # split provided environment variables into exports vs unsets
        for name, value in kwargs.items():
            if value is None:
                unset_vars.append(name.upper())
            else:
                export_vars[name.upper()] = value

        if export_metavars:
            # split meta variables into exports vs unsets
            for name, value in context.conda_exe_vars_dict.items():
                if value is None:
                    unset_vars.append(name.upper())
                elif "/" in value or "\\" in value:
                    export_vars[name.upper()] = self.path_conversion(value)
                else:
                    export_vars[name.upper()] = value
        else:
            # unset all meta variables
            unset_vars.extend(context.conda_exe_vars_dict)

        return export_vars, unset_vars

    def _build_activate_stack(self, env_name_or_prefix: str, stack: bool) -> dict:
        """
        Build dictionary with the following key-value pairs, to be used in creating the new
        environment to be activated:
            unset_vars: list containing environmental variables to be unset
            set_vars: dictionary containing environmental variables to be set, as key-value pairs
            export_vars: dictionary containing environmental variables to be exported, as
                key-value pairs
            deactivate_scripts: tuple containing scripts associated with installed packages
                that should be run on deactivation (from `deactivate.d`), if any
            activate_scripts: tuple containing scripts associated with installed packages
                that should be run on activation (from `activate.d`), if any
        """
        # get environment prefix
        if re.search(r"\\|/", env_name_or_prefix):
            prefix = expand(env_name_or_prefix)
            if not os.path.isdir(os.path.join(prefix, "conda-meta")):
                from conda.exceptions import EnvironmentLocationNotFound

                raise EnvironmentLocationNotFound(prefix)
        elif env_name_or_prefix in (ROOT_ENV_NAME, "root"):
            prefix = context.root_prefix
        else:
            prefix = locate_prefix_by_name(env_name_or_prefix)

        # get prior shlvl and prefix
        old_conda_shlvl = int(self.environ.get("CONDA_SHLVL", "").strip() or 0)
        old_conda_prefix = self.environ.get("CONDA_PREFIX")

        # if the prior active prefix is this prefix we are actually doing a reactivate
        if old_conda_prefix == prefix and old_conda_shlvl > 0:
            return self.build_reactivate()

        activate_scripts = self._get_activate_scripts(prefix)
        conda_shlvl = old_conda_shlvl + 1
        conda_default_env = self._default_env(prefix)
        env_vars = {
            name: value
            for name, value in self._get_environment_env_vars(prefix).items()
            if value != CONDA_ENV_VARS_UNSET_VAR
        }

        # get clobbered environment variables
        clobber_vars = set(env_vars.keys()).intersection(self.environ.keys())
        clobber_vars = set(
            filter(lambda var: env_vars[var] != self.environ[var], clobber_vars)
        )
        if clobber_vars:
            print(
                "WARNING: overwriting environment variables set in the machine",
                file=sys.stderr,
            )
            print(f"overwriting variable {clobber_vars}", file=sys.stderr)
        for name in clobber_vars:
            env_vars[f"__CONDA_SHLVL_{old_conda_shlvl}_{name}"] = self.environ.get(name)

        if old_conda_shlvl == 0:
            export_vars, unset_vars = self.get_export_unset_vars(
                path=self.pathsep_join(self._add_prefix_to_path(prefix)),
                conda_prefix=prefix,
                conda_shlvl=conda_shlvl,
                conda_default_env=conda_default_env,
                **env_vars,
            )
            deactivate_scripts = ()
        elif stack:
            export_vars, unset_vars = self.get_export_unset_vars(
                path=self.pathsep_join(self._add_prefix_to_path(prefix)),
                conda_prefix=prefix,
                conda_shlvl=conda_shlvl,
                conda_default_env=conda_default_env,
                **env_vars,
                **{
                    f"CONDA_PREFIX_{old_conda_shlvl}": old_conda_prefix,
                    f"CONDA_STACKED_{conda_shlvl}": "true",
                },
            )
            deactivate_scripts = ()
        else:
            export_vars, unset_vars = self.get_export_unset_vars(
                path=self.pathsep_join(
                    self._replace_prefix_in_path(old_conda_prefix, prefix)
                ),
                conda_prefix=prefix,
                conda_shlvl=conda_shlvl,
                conda_default_env=conda_default_env,
                **env_vars,
                **{
                    f"CONDA_PREFIX_{old_conda_shlvl}": old_conda_prefix,
                },
            )
            deactivate_scripts = self._get_deactivate_scripts(old_conda_prefix)

        set_vars = {}

        return {
            "unset_vars": unset_vars,
            "set_vars": set_vars,
            "export_vars": export_vars,
            "deactivate_scripts": deactivate_scripts,
            "activate_scripts": activate_scripts,
        }

    def build_deactivate(self) -> dict:
        """
        Build dictionary with the following key-value pairs, to be used in creating the new
        environment to be activated (that is, the previous environment used):
            unset_vars: list containing environmental variables to be unset
            set_vars: dictionary containing environmental variables to be set, as key-value pairs
            export_vars: dictionary containing environmental variables to be exported, as
                key-value pairs
            deactivate_scripts: tuple containing scripts associated with installed packages
                that should be run on deactivation (from `deactivate.d`), if any
            activate_scripts: tuple containing scripts associated with installed packages
                that should be run on activation (from `activate.d`), if any
        """
        self._deactivate = True
        # query environment
        old_conda_prefix = self.environ.get("CONDA_PREFIX")
        old_conda_shlvl = int(self.environ.get("CONDA_SHLVL", "").strip() or 0)
        if not old_conda_prefix or old_conda_shlvl < 1:
            # no active environment, so cannot deactivate; do nothing
            return {
                "unset_vars": (),
                "set_vars": {},
                "export_vars": {},
                "deactivate_scripts": (),
                "activate_scripts": (),
            }
        deactivate_scripts = self._get_deactivate_scripts(old_conda_prefix)
        old_conda_environment_env_vars = self._get_environment_env_vars(
            old_conda_prefix
        )

        new_conda_shlvl = old_conda_shlvl - 1
        set_vars = {}
        if old_conda_shlvl == 1:
            new_path = self.pathsep_join(
                self._remove_prefix_from_path(old_conda_prefix)
            )
            # You might think that you can remove the CONDA_EXE vars with export_metavars=False
            # here so that "deactivate means deactivate" but you cannot since the conda shell
            # scripts still refer to them and they only set them once at the top. We could change
            # that though, the conda() shell function could set them instead of doing it at the
            # top.  This would be *much* cleaner. I personally cannot abide that I have
            # deactivated conda and anything at all in my env still references it (apart from the
            # shell script, we need something I suppose!)
            export_vars, unset_vars = self.get_export_unset_vars(
                conda_prefix=None,
                conda_shlvl=new_conda_shlvl,
                conda_default_env=None,
            )
            activate_scripts = ()
            export_path = {
                "PATH": new_path,
            }
        else:
            assert old_conda_shlvl > 1
            new_prefix = self.environ.get("CONDA_PREFIX_%d" % new_conda_shlvl)
            conda_default_env = self._default_env(new_prefix)
            new_conda_environment_env_vars = self._get_environment_env_vars(new_prefix)

            old_prefix_stacked = "CONDA_STACKED_%d" % old_conda_shlvl in self.environ
            new_path = ""

            unset_vars = ["CONDA_PREFIX_%d" % new_conda_shlvl]
            if old_prefix_stacked:
                new_path = self.pathsep_join(
                    self._remove_prefix_from_path(old_conda_prefix)
                )
                unset_vars.append("CONDA_STACKED_%d" % old_conda_shlvl)
            else:
                new_path = self.pathsep_join(
                    self._replace_prefix_in_path(old_conda_prefix, new_prefix)
                )

            export_vars, unset_vars2 = self.get_export_unset_vars(
                conda_prefix=new_prefix,
                conda_shlvl=new_conda_shlvl,
                conda_default_env=conda_default_env,
                **new_conda_environment_env_vars,
            )
            unset_vars += unset_vars2
            export_path = {
                "PATH": new_path,
            }
            activate_scripts = self._get_activate_scripts(new_prefix)

        for env_var in old_conda_environment_env_vars.keys():
            unset_vars.append(env_var)
            save_var = f"__CONDA_SHLVL_{new_conda_shlvl}_{env_var}"
            if save_var in self.environ.keys():
                export_vars[env_var] = self.environ[save_var]
        return {
            "unset_vars": unset_vars,
            "set_vars": set_vars,
            "export_vars": export_vars,
            "export_path": export_path,
            "deactivate_scripts": deactivate_scripts,
            "activate_scripts": activate_scripts,
        }

    def build_reactivate(self) -> dict:
        """
        Build dictionary with the following key-value pairs, to be used in updating the
        environment mapping:
            unset_vars: list containing environmental variables to be unset
            set_vars: dictionary containing environmental variables to be set, as key-value pairs
            export_vars: dictionary containing environmental variables to be exported, as
                key-value pairs
            deactivate_scripts: tuple containing scripts associated with installed packages
                that should be run on deactivation (from `deactivate.d`), if any
            activate_scripts: tuple containing scripts associated with installed packages
                that should be run on activation (from `activate.d`), if any
        """
        self._reactivate = True
        conda_prefix = self.environ.get("CONDA_PREFIX")
        conda_shlvl = int(self.environ.get("CONDA_SHLVL", "").strip() or 0)
        if not conda_prefix or conda_shlvl < 1:
            # no active environment, so cannot reactivate; do nothing
            return {
                "unset_vars": (),
                "set_vars": {},
                "export_vars": {},
                "deactivate_scripts": (),
                "activate_scripts": (),
            }
        new_path = self.pathsep_join(
            self._replace_prefix_in_path(conda_prefix, conda_prefix)
        )
        set_vars = {}

        env_vars_to_unset = ()
        env_vars_to_export = {
            "PATH": new_path,
            "CONDA_SHLVL": conda_shlvl,
        }
        conda_environment_env_vars = self._get_environment_env_vars(conda_prefix)
        for k, v in conda_environment_env_vars.items():
            if v == CONDA_ENV_VARS_UNSET_VAR:
                env_vars_to_unset = env_vars_to_unset + (k,)
            else:
                env_vars_to_export[k] = v
        # environment variables are set only to aid transition from conda 4.3 to conda 4.4
        return {
            "unset_vars": env_vars_to_unset,
            "set_vars": set_vars,
            "export_vars": env_vars_to_export,
            "deactivate_scripts": self._get_deactivate_scripts(conda_prefix),
            "activate_scripts": self._get_activate_scripts(conda_prefix),
        }

    def _get_starting_path_list(self):
        # For isolation, running the conda test suite *without* env. var. inheritance
        # every so often is a good idea. We should probably make this a pytest fixture
        # along with one that tests both hardlink-only and copy-only, but before that
        # conda's testsuite needs to be a lot faster!
        clean_paths = {
            "darwin": "/usr/bin:/bin:/usr/sbin:/sbin",
            # You may think 'let us do something more clever here and interpolate
            # `%windir%`' but the point here is the the whole env. is cleaned out
            "win32": "C:\\Windows\\system32;"
            "C:\\Windows;"
            "C:\\Windows\\System32\\Wbem;"
            "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\",
        }
        path = self.environ.get(
            "PATH",
            clean_paths[sys.platform] if sys.platform in clean_paths else "/usr/bin",
        )
        path_split = path.split(os.pathsep)
        return path_split

    def _get_path_dirs(self, prefix, extra_library_bin=False):
        if on_win:  # pragma: unix no cover
            yield prefix.rstrip("\\")
            yield self.sep.join((prefix, "Library", "mingw-w64", "bin"))
            yield self.sep.join((prefix, "Library", "usr", "bin"))
            yield self.sep.join((prefix, "Library", "bin"))
            yield self.sep.join((prefix, "Scripts"))
            yield self.sep.join((prefix, "bin"))
        else:
            yield self.sep.join((prefix, "bin"))

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
        old_conda_shlvl = int(self.environ.get("CONDA_SHLVL", "").strip() or 0)
        if not old_conda_shlvl and not any(p.endswith("condabin") for p in path_list):
            condabin_dir = self.path_conversion(
                os.path.join(context.conda_prefix, "condabin")
            )
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
                            f"Did not find path entry {prefix_dirs[prefix_dirs_idx]}",
                            file=sys.stderr,
                        )
                    prefix_dirs_idx = prefix_dirs_idx - 1
                # this compensates for an extra Library/bin dir entry from the interpreter on
                #     windows.  If that entry isn't being added, it should have no effect.
                library_bin_dir = self.path_conversion(
                    self.sep.join((sys.prefix, "Library", "bin"))
                )
                if path_list[last_idx + 1] == library_bin_dir:
                    last_idx += 1
                del path_list[first_idx : last_idx + 1]
        else:
            first_idx = 0

        if new_prefix is not None:
            path_list[first_idx:first_idx] = list(self._get_path_dirs(new_prefix))

        return tuple(path_list)

    def _default_env(self, prefix):
        if paths_equal(prefix, context.root_prefix):
            return "base"
        return (
            os.path.basename(prefix)
            if os.path.basename(os.path.dirname(prefix)) == "envs"
            else prefix
        )

    def _get_activate_scripts(self, prefix):
        _script_extension = self.script_extension
        se_len = -len(_script_extension)
        try:
            paths = (
                entry.path
                for entry in os.scandir(
                    os.path.join(prefix, "etc", "conda", "activate.d")
                )
            )
        except OSError:
            return ()
        return self.path_conversion(
            sorted(p for p in paths if p[se_len:] == _script_extension)
        )

    def _get_deactivate_scripts(self, prefix):
        _script_extension = self.script_extension
        se_len = -len(_script_extension)
        try:
            paths = (
                entry.path
                for entry in os.scandir(
                    os.path.join(prefix, "etc", "conda", "deactivate.d")
                )
            )
        except OSError:
            return ()
        return self.path_conversion(
            sorted((p for p in paths if p[se_len:] == _script_extension), reverse=True)
        )

    def _get_environment_env_vars(self, prefix):
        env_vars_file = os.path.join(prefix, PREFIX_STATE_FILE)
        pkg_env_var_dir = os.path.join(prefix, PACKAGE_ENV_VARS_DIR)
        env_vars = {}

        # First get env vars from packages
        if os.path.exists(pkg_env_var_dir):
            for pkg_env_var_path in sorted(
                entry.path for entry in os.scandir(pkg_env_var_dir)
            ):
                with open(pkg_env_var_path) as f:
                    env_vars.update(json.loads(f.read()))

        # Then get env vars from environment specification
        if os.path.exists(env_vars_file):
            with open(env_vars_file) as f:
                prefix_state = json.loads(f.read())
                prefix_state_env_vars = prefix_state.get("env_vars", {})
                dup_vars = [
                    ev for ev in env_vars.keys() if ev in prefix_state_env_vars.keys()
                ]
                for dup in dup_vars:
                    print(
                        "WARNING: duplicate env vars detected. Vars from the environment "
                        "will overwrite those from packages",
                        file=sys.stderr,
                    )
                    print("variable %s duplicated" % dup, file=sys.stderr)
                env_vars.update(prefix_state_env_vars)

        return env_vars
