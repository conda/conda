[//]: # (current developments)

## 24.7.0 (2024-07-17)

### Enhancements

* MSYS2 packages can now use the upstream installation prefixes. (#13649)
* Add a new `reporters` setting for configure output. (#13736)
* Report traceback of plugin loading errors with verbosity 2 or higher (`-vv` or more). (#13742 via #13846)
* Skip checking for `.pyc` and `.pyo` files in the `conda doctor` "missing files" health check. (#13370 via #13931)
* **Breaking change**  `conda list --explicit` will not print authentication details by default. A new flag `--auth` has been added so folks can opt-in to this behaviour. (#13936)
* Print transaction report for `@EXPLICIT` lockfile installs too. (#13940)
* Do not require `-n/--name` or `-p/--prefix` if `conda create` is invoked with `--dry-run`. (#13941)
Add an `envvars_force_uppercase` setting which defaults to `True`, uppercasing all environment variables (thereby justifying `conda`'s current behaviour); when `envvars_force_uppercase` is set to `False`, conda will only save preserved-case variable names. (#13713 via #13943)
* Alias `conda env list` command to `conda info --envs`. (#13972)

### Bug fixes

* Improve treatment of logger levels (#13735)
* Mask authentication details in `conda-meta/*.json` metadata. (#13937)
* Mask Anaconda.org tokens in verbose logs. (#13939, #13987)
* Fixes parsing error when history file only contains a single commented line (#13960)
* Add missing `emscripten` and `wasi` entries to the recognized platforms, and `wasm32` to the recognized architectures. (#13095)
* Checksum comparisons in `conda.gateways.connection.download.download()` are not case sensitive anymore. (#13969)
* Disallow some more characters in Windows for prefix names (`^`, `%`, `!`, `=`, `(`, `)`, `\`). These characters complicate or prevent environment activation if present. (#12558 via #13975)
* Fix caching when `repodata.json` contains `\r\n` line endings. (#14002 via #14003)
* Fix binary_replace not matching chunks that end with `\n`. (#14043 via #14044)

### Deprecations

* Mark `conda.gateways.logging.initialize_root_logger` as pending deprecation. (#13735, #14046)
* Mark `conda.cli.main_env_list.execute` as pending deprecation. Use `conda.cli.main_info.execute` instead. (#13972)
* Revert `--all` deprecation in `conda info`. (#14004)
* Mark `conda.exports.iteritems` as pending deprecation. Use builtin `dict.items()` instead. (#14034)
* Mark `conda.exports.Completer` as pending deprecation. (#14034)
* Mark `conda.exports.InstalledPackages` as pending deprecation. (#14034)
* Mark `conda.exports.KEYS` as pending deprecation. (#14034)
* Mark `conda.exports.KEYS_DIR` as pending deprecation. (#14034)
* Mark `conda.exports.hash_file` as pending deprecation. (#14034)
* Mark `conda.exports.verify` as pending deprecation. (#14034)
* Mark `conda.exports.symlink_conda` as pending deprecation. Use `conda.activate` instead. (#14034)
* Mark `conda.exports._symlink_conda_hlp` as pending deprecation. Use `conda.activate` instead. (#14034)
* Mark `conda.exports.win_conda_bat_redirect` as pending deprecation. Use `conda.activate` instead. (#14034)
* Mark `conda.utils.win_path_to_cygwin` as pending deprecation. Use `conda.common.path.win_path_to_unix` instead. (#14034)
* Mark `conda.utils.cygwin_path_to_win` as pending deprecation. Use `conda.utils.unix_path_to_win` instead. (#14034)
* Mark `conda.utils.translate_stream` as pending deprecation. (#14034)
* Mark `conda.utils.unix_shell_base` as pending deprecation. Use `conda.activate` instead. (#14034)
* Mark `conda.utils.msys2_shell_base` as pending deprecation. Use `conda.activate` instead. (#14034)
* Mark `conda.utils.shells` as pending deprecation. Use `conda.activate` instead. (#14034)

### Docs

* Clarify proxy server configuration in documentation. (#12856)
* Added type hints and doc strings to `conda.core.envs_manager`. (#13817)
* Add logging overview as deep-dive (#13735)
* Update conda cheatsheet text and add it directly to cheatsheet page. (#13889)
* Added cheatsheet PDF download to cheatsheet page. (#13909)
* Added `ssl_verify: truststore` to the user guide. (#13935)
* Fixed the help text of the `satisfied-skip-solve` flag. (#13946)
* Add a section explaining how to correctly raise exceptions from a plugin. (#13741 via #13950)
* Add new article for configuring `envs_dirs` and `pkgs_dirs`. (#13954)

### Other

* Replace calls to logger.warn with logger.warning (#13963)

### Contributors

* @beeankha
* @conda-bot
* @erik-whiting made their first contribution in https://github.com/conda/conda/pull/13877
* @ifitchet
* @jaimergp
* @jezdez
* @kathatherine
* @kelvinou01 made their first contribution in https://github.com/conda/conda/pull/14044
* @kenodegard
* @zklaus
* @ForgottenProgramme
* @Nathann03
* @zeehio
* @skupr-anaconda made their first contribution in https://github.com/conda/conda/pull/13946
* @tl-hbk
* @DerThorsten made their first contribution in https://github.com/conda/conda/pull/13962
* @travishathaway
* @dependabot[bot]
* @padeoe made their first contribution in https://github.com/conda/conda/pull/12856
* @pre-commit-ci[bot]



## 24.5.0 (2024-05-08)

### Enhancements

* Report which `MatchSpec` item caused `Invalid*Spec` exceptions for more informative error messages. (#11203 via #13598)
* MSYS2 packages can now use the upstream installation prefixes. (#13649)
* Add support for CEP-15 `base_url` field in `repodata.json`. (#13137 via #13744)
* In custom channel settings, allow specification of channel URLs using a glob-like wildcard pattern, e.g. for user with auth handler plugins. (#13778 via #13779)

### Bug fixes

* Fix `conda notices --json` to correctly output JSON. (#13561)
* Fix prefix replacement for Windows `subdir` on Unix. (#13689)

### Deprecations

* Mark `conda.plan._get_best_prec_match` as pending deprecation. Use `conda.misc._get_best_prec_match` instead. (#12421)
* Mark `conda.plan._handle_menuinst` as pending deprecation. (#12421)
* Mark `conda.plan._inject_UNLINKLINKTRANSACTION` as pending deprecation. (#12421)
* Mark `conda.plan._plan_from_actions` as pending deprecation. (#12421)
* Mark `conda.plan.add_defaults_to_specs` as pending deprecation. (#12421)
* Mark `conda.plan.add_unlink` as pending deprecation. (#12421)
* Mark `conda.plan.display_actions` as pending deprecation. (#12421)
* Mark `conda.plan.execute_actions` as pending deprecation. (#12421)
* Mark `conda.plan.get_blank_actions` as pending deprecation. (#12421)
* Mark `conda.plan.install_actions` as pending deprecation. (#12421)
* Mark `conda.plan.print_dists` as pending deprecation. (#12421)
* Mark `conda.plan.revert_actions` as pending deprecation. Use `conda.cli.install.revert_actions` instead. (#12421)
* Mark `conda.plan` as an entrypoint as pending deprecation. (#12421)
* Mark `conda.activate._Activator.add_export_unset_vars` as pending deprecation. Use `conda.activate._Activator.get_export_unset_vars` instead. (#13720)
* Mark `conda.activate._Activator.get_scripts_export_unset_vars` as pending deprecation. Use `get_scripts_export_unset_vars` helper function in `test_activate.py` instead. (#13720)
* Mark `conda.activate._Activator._get_path_dirs(extra_library_bin)` as pending deprecation. (#13720)
* Mark `conda.activate.JSONFormatMixin.get_scripts_export_unset_vars` as pending deprecation. Use `conda.activate._Activator.get_export_unset_vars` instead. (#13720)
* Mark `conda.gateways.logging.trace` as pending deprecation. Use `Logger.log(conda.common.constants.TRACE, msg)` instead. (#13732)
* Mark `conda create --mkdir` as pending deprecation. The argument is redundant and unnecessary. (#13751)
* Mark `conda install --mkdir` as pending deprecation. Use `conda create` instead. (#13751)
* Mark `conda._vendor.frozendict` as pending deprecation. Use `frozendict` instead. (#13767 via #13766)
* Mark `conda.auxlib.collection.make_immutable` as pending deprecation. Use `frozendict.deepfreeze` instead. (#13801)
* Mark `conda.plan.execute_plan` as pending deprecation. (#13869)
* Mark `conda.plan.execute_instructions` as pending deprecation. (#13869)
* Mark `conda.plan._update_old_plan` as pending deprecation. (#13869)

### Docs

* Add type hints and doc strings to `conda.core.index`. (#13816)

### Other

* Remove `setuptools` remainings (`MANIFEST.in`, `wheel` build dependency) not required since the move to `hatch` in #12509. (#13684)
* Remove and update any imports inside conda that is importing from `conda/exports.py`. (#13869)

### Contributors

* @beeankha
* @conda-bot
* @dbast
* @ifitchet made their first contribution in https://github.com/conda/conda/pull/13649
* @isuruf
* @jaimergp
* @jezdez
* @kenodegard
* @zklaus
* @ForgottenProgramme
* @mattkram
* @Nathann03 made their first contribution in https://github.com/conda/conda/pull/13816
* @dwr-psandhu made their first contribution in https://github.com/conda/conda/pull/13770
* @travishathaway
* @dependabot[bot]
* @pre-commit-ci[bot]



## 24.4.0 (2024-04-24)

### Enhancements

* For Windows users, the stub executables used for Python entrypoints in packages are now codesigned. (#13721)

### Contributors

* @dholth
* @jezdez
* @Callek made their first contribution in https://github.com/conda/conda/pull/13721


## 24.3.0 (2024-03-12)

### Enhancements

* Show first few characters of undecodeable response if `repodata.json` raises
  `JSONDecodeError`. (#11804)
* Update `conda.gateways.subprocess.subprocess_call` to use `text=True` to avoid manual encoding/decoding. (#13240)
* Add a new plugin hook giving plugin authors the ability to define new settings. (#13554)
* Optimize module imports to speed up `conda activate`. (#13567 via #13568)
* Move `conda env export` to `conda export` and alias the old command to the new command. (#13577)
* Report progress while running `conda install --revision <idx>`. (#13611)
* Add `conda.testing.tmp_channel` pytest fixture to create a temporary local channel for testing. (#13634)

### Bug fixes

* Print traceback on `KeyboardInterrupt` instead of raising another `AttributeError` exception, when conda debugging logs are enabled. (#13531)
* Parse integer channel notice IDs as `str` instead of raising an exception. (#13543)
* Add direct runtime dependency on `zstandard` for use when downloading `repodata.json.zst`. (#13551)
* Fallback to `repodata.json` if `repodata.json.zst` cannot be decompressed as `zstandard`. (#13558)
* `conda rename` command no longer throws an error when conda is not active. (#13565)
* Fallback to `repodata.json` from `repodata.json.zst` on most 4xx error codes. (#13573)
* Fix excess resource usage by log handling when fetching repodata. (#13541 via #13628)
* Re-enable `--subdir` and `--platform` flags to be available for `conda env create` command. (#13632)
* Fix `__archspec` virtual package on Windows to return microarchitecture instead of the default `x86_64`. (#13641)
* Check `Content-Length` is nonzero before calculating progress, avoiding a possible `ZeroDivisionError`. (#13653, #13671)

### Deprecations

* Discontinue custom docker images. Use images provided by [Anaconda Inc.](https://hub.docker.com/r/continuumio/miniconda3) or [conda-forge](https://hub.docker.com/r/condaforge/miniforge3) instead. (#13162)
* Mark `conda.common.compat.encode_arguments` as pending deprecation. (#13240)
* Remove `conda.export.handle_proxy_407`. (#13629)
* Mark `conda.testing.integration.make_temp_channel` as pending deprecation. Use `conda.testing.tmp_channel` fixture instead. (#13634)
* Mark `conda.testing.integration.running_a_python_capable_of_unicode_subprocessing` as pending deprecation. (#13634)
* Mark `conda.testing.integration.set_tmpdir` as pending deprecation. Use `tmp_path`, `conda.testing.path_factory`, or `conda.testing.tmp_env` instead. (#13634)
* Mark `conda.testing.integration._get_temp_prefix` as pending deprecation. Use `tmp_path`, `conda.testing.path_factory`, or `conda.testing.tmp_env` instead. (#13634)
* Mark `conda.testing.integration.make_temp_prefix` as pending deprecation. Use `tmp_path`, `conda.testing.path_factory`, or `conda.testing.tmp_env` instead. (#13634)
* Mark `conda.testing.integration.FORCE_temp_prefix` as pending deprecation. Use `tmp_path`, `conda.testing.path_factory`, or `conda.testing.tmp_env` instead. (#13634)
* Mark `conda.testing.integration.create_temp_location` as pending deprecation. Use `tmp_path` or `conda.testing.path_factory` instead. (#13634)
* Mark `conda.testing.integration.tempdir` as pending deprecation. Use `tmp_path` or `conda.testing.path_factory` instead. (#13634)
* Mark `conda.testing.integration.reload_config` as pending deprecation. Use `conda.base.context.reset_context` instead. (#13634)
* Postpone `conda.base.context.Context.conda_exe` deprecation to `conda 24.9`. (#13634)
* Postpone `conda.testing.integration.run_command` deprecation to `conda 25.3`. (#13634)
* Postpone loading subcommands from executables deprecation to `conda 25.3`. (#13634)
* Remove vendored `conda._vendor.boltons`. Use `boltons` package instead. (#12681 via #13634)
* Remove `conda.auxlib.packaging`. Use a modern build system instead; see https://packaging.python.org/en/latest/tutorials/packaging-projects#creating-pyproject-toml for more details. (#12681 via #13634)
* Remove `conda env create --force`. Use `conda env create --yes` instead. (#12681 via #13634)
* Remove `conda info PACKAGE`. Use `conda search PACKAGE --info` instead. (#12681 via #13634)
* Remove `conda.core.subdir_data.fetch_repodata_remote_request`. Use `conda.core.subdir_data.SubdirData.repo_fetch.fetch_latest_parsed` instead." (#12681 via #13634)
* Remove `conda.exports.memoized`. Use `functools.lru_cache` instead. (#12681 via #13634)
* Remove `conda.gateways.disk.read._digest_path`. Use `conda.gateways.disk.read.compute_sum` instead. (#12681 via #13634)
* Remove `conda.gateways.disk.read.compute_md5sum`. Use `conda.gateways.disk.read.compute_sum(path, "md5")` instead. (#12681 via #13634)
* Remove `conda.gateways.disk.read.compute_sha256sum`. Use `conda.gateways.disk.read.compute_sum(path, "sha256")` instead. (#12681 via #13634)
* Remove `conda.instructions.PREFIX`. (#12681 via #13634)
* Remove `conda.instructions.PREFIX_CMD`. (#12681 via #13634)
* Remove `conda.testing.encode_for_env_var`. (#12681 via #13634)
* Remove `conda.testing.conda_check_versions_aligned`. (#12681 via #13634)
* Remove `conda.testing.helpers.run_inprocess_conda_command`. Use `conda.testing.tmp_env` instead. (#12681 via #13634)
* Remove `conda.testing.helpers.capture_json_with_argv`. (#12681 via #13634)
* Remove `conda.testing.integration.get_conda_list_tuple`. Use `conda.core.prefix_data.PrefixData.get` instead. (#12681 via #13634)
* Remove `conda.utils.md5_file`. Use `conda.gateways.disk.read.compute_sum(path, "md5")` instead. (#12681 via #13634)
* Remove `conda.utils.hashsum_file`. Use `conda.gateways.disk.read.compute_sum` instead. (#12681 via #13634)
* Remove `conda.utils.safe_open`. Use `open` instead. (#12681 via #13634)
* Remove `python -m conda_env`. Use `conda env` or `python -m conda env` instead. (#12681 via #13634)
* Remove `conda_env.env.load_from_directory`. (#12681 via #13634)
* Remove `conda_env.pip_util.get_pip_version`. (#12681 via #13634)
* Remove `conda_env.pip_util.PipPackage`. (#12681 via #13634)
* Remove `conda_env.pip_util.installed`. (#12681 via #13634)
* Remove `conda_env.pip_util._canonicalize_name`. (#12681 via #13634)
* Remove `conda_env.pip_util.add_pip_installed`. (#12681 via #13634)

### Docs

* Update the navigation links for Miniconda. (#13572)

### Other

* Remove `dev/*` scripts in favor of `conda-incubator/setup-miniconda` GitHub Action in `.github/workflows/tests.yml`. (#13162)
* Stop chaining commands for steps in `.github/workflows/tests.yml`.  (#12418 via #13162)
* Modernize tests. (#13547, #13292)
* Run GitHub tests workflow also on `osx-arm64` (aka Apple Silicon) runners. Enable `osx-arm64` canary builds. Fix or disable broken tests. (#13617)
* Upload stable release artifacts to GitHub releases during releases. (#13399)

### Contributors

* @beeankha
* @conda-bot
* @dbast
* @dholth
* @FFY00
* @isuruf
* @jaimergp
* @jezdez
* @jjhelmus
* @kenodegard
* @zklaus made their first contribution in https://github.com/conda/conda/pull/13579
* @ForgottenProgramme
* @mbargull
* @travishathaway
* @pre-commit-ci[bot]



## 24.1.2 (2024-02-15)

### Bug fixes

* Fix deprecated `fetch_repodata_remote_request` when `repodata_use_zst` is enabled. (#13595)

### Contributors

* @dholth



## 24.1.1 (2024-02-12)

### Bug fixes

* Fallback to `repodata.json` if `repodata.json.zst` cannot be decompressed as zstandard. (#13558)
* Fallback to `repodata.json` from `repodata.json.zst` on most 4xx error codes. (#13573)

### Contributors

* @dholth



## 24.1.0 (2024-01-24)

### Special announcement

#### The `conda_env.*` modules have been merged into the `conda` package!

To improve the integration of the `conda env` subcommand (previously standalone), we've moved its
code into the `conda` package, while allowing old `conda env` commands to still work via Python
import redirects. This is a first step of many to improving the user experience of the conda
command line interface related to environment management. (#13168)

### Enhancements

* Verify signatures on to-be-installed packages instead of on all packages. (#11545, #13053)
* Add new `pre-solves` and `post-solves` plugin hooks. (#13053)
* Add support for Python 3.12. (#13072)
* Check `repodata.json.zst` for faster repodata downloads. (#13256)
* Add `--skip-flexible-search` option in `conda search` to skip flexible search. (#13315)
* Provide a more useful warning when attempting to rename a non-existent prefix. (#13387)
* Add a new flag `--keep-env` to be used with `conda remove --all`. It allows users to delete all packages in the environment while retaining the environment itself. (#13419)
* Add a Y/N prompt warning users that `conda env remove` and `conda remove --all` deletes not only the conda packages but the entirety of the specified environment. (#13440)
* Add `--repodata-use-zst/--no-repodata-use-zst` flag to control `repodata.json.zst` check; corresponding `repodata_use_zst: true/false` for `.condarc`. Default is to check for `repodata.json.zst`. Disable if remote returns unparseable `repodata.json.zst` instead of correct data or 404. (#13504)


### Bug fixes

* Create the `~/.conda` directory before trying to write to the `environments.txt` file. (#13338)
* Ensure `PackageRecord.timestamp` is dumped in milliseconds. (#13483)
* Fix error when setting a non-default repodata filename via `CONDA_REPODATA_FNS`. (#13490)
* Fix the config file location where the integrated Anaconda client gateway loads user configuration from. This is a regression introduced in conda 23.11.0 when the `platformdirs` library was adopted. (#13517 via #13520)
* Interpret missing `Cache-Control` header as `max-age=0` instead of exception. (#13522)

### Deprecations

* Mark `conda_env/cli/common` as pending deprecation. Use `conda.cli.common` instead. (#13168)
* Mark `conda_env/cli/main_config` as pending deprecation. Use `conda.cli.main_env_config` instead. (#13168)
* Mark `conda_env/cli/main_create` as pending deprecation. Use `conda.cli.main_env_create` instead. (#13168)
* Mark `conda_env/cli/main_export` as pending deprecation. Use `conda.cli.main_env_export` instead. (#13168)
* Mark `conda_env/cli/main_list` as pending deprecation. Use `conda.cli.main_env_list` instead. (#13168)
* Mark `conda_env/cli/main_remove` as pending deprecation. Use `conda.cli.main_env_remove` instead. (#13168)
* Mark `conda_env/cli/main_update` as pending deprecation. Use `conda.cli.main_env_update` instead. (#13168)
* Mark `conda_env/cli/main_vars` as pending deprecation. Use `conda.cli.main_env_vars` instead. (#13168)
* Mark `conda_env/env` as pending deprecation. Use `conda.env.env` instead. (#13168)
* Mark `conda_env/installers/base` as pending deprecation. Use `conda.env.installers.base` instead. (#13168)
* Mark `conda_env/installers/conda` as pending deprecation. Use `conda.env.installers.conda` instead. (#13168)
* Mark `conda_env/installers/pip` as pending deprecation. Use `conda.env.installers.pip` instead. (#13168)
* Mark `conda_env/pip_util` as pending deprecation. Use `conda.env.pip_util` instead. (#13168)
* Mark `conda_env/specs` as pending deprecation. Use `conda.env.specs` instead. (#13168)
* Mark `conda_env/specs/binstar` as pending deprecation. Use `conda.env.specs.binstar` instead. (#13168)
* Mark `conda_env/specs/requirements` as pending deprecation. Use `conda.env.specs.requirements` instead. (#13168)
* Mark `conda_env/specs/yaml_file` as pending deprecation. Use `conda.env.specs.yaml_file` instead. (#13168)
* Mark `conda.testing.integration.make_temp_package_cache` as pending deprecation. (#13511)

### Docs

* Update Getting Started documentation in User Guide. (#13190)
* Add GoatCounter (https://www.goatcounter.com/) as an analytics tool. (#13384)
* Add type hints and doc strings to `conda.cli.main_info`. (#13445)
* Add type hints and doc strings to `conda.cli.main_search`. (#13465)

### Other

* Add type hinting for `VersionOrder` class. (#13380)
* Re-enable and apply `pyupgrade` via `ruff`. (#13272, #13433)
* Start tracking performance in continuous integration and automatically report about it in pull requests. (#13460)
* Add `tmp_pkgs_dir` fixture to replace `make_temp_package_cache`. (#13511)
* Improve lock API for the repodata cache. (#13455)

### Contributors

* @beeankha
* @conda-bot
* @dbast
* @dholth
* @jaimergp
* @jezdez
* @johnnynunez
* @kathatherine
* @kenodegard
* @ForgottenProgramme
* @marcoesters
* @mfansler
* @schuylermartin45 made their first contribution in https://github.com/conda/conda/pull/13385
* @travishathaway
* @pre-commit-ci[bot]
* @samhaese made their first contribution in https://github.com/conda/conda/pull/13465



## 23.11.0 (2023-11-30)

### Special announcement

New [`menuinst` v2](https://github.com/conda/menuinst/releases/tag/2.0.0) support!

`conda` has supported Start menu items on Windows for a long time. This is what allows users to open up their Miniconda prompt on CMD (Command Prompt) with an initialized `conda` session. This menu item (or shortcut) creation logic is provided by the `menuinst` package.

With the release of 23.11.0, `conda` now supports [`menuinst` v2](https://github.com/conda/menuinst/releases/tag/2.0.0), which enables the same experience across Windows, Linux, and macOS. This means package builders will be able to provide desktop icons across all operating systems, which can be especially useful for GUI applications. See the [documentation](https://conda.github.io/menuinst/) for more details.

If you don't want `conda` to create shortcuts, you can disable it via:

- `shortcuts: false` entry in your `.condarc` configuration
- `CONDA_SHORTCUTS=false` environment variable
- `--no-shortcuts` command-line flag


### Enhancements

* Add support for `menuinst` v2, enabling shortcuts across all platforms (Windows, Linux, macOS) using a new JSON schema (see [CEP-11](https://github.com/conda-incubator/ceps/blob/main/cep-11.md)). Retain support for old v1-style JSON menus. (#11882)
* Stop using vendored `chardet` package by `requests`/`pip`; explicitly depend on `charset_normalizer`. (#13171)
* Introduce a new plugin hook, `CondaHealthCheck`, as part of `conda doctor`. (#13186)
* Include `activate` and `deactivate` in the `--help` command list. (#13191)
* Prioritize download of larger packages to prevent smaller ones from waiting. (#13248)
* Display the used solver in `conda info` output for debugging purposes. (#13265)
* Add `__conda` virtual package. (#13266)
* Switch from `appdirs` to `platformdirs`. (#13306)
* Implement resume capability for interrupted package downloads. (#8695)

### Bug fixes

* Log expected JLAP range-request errors at `info` level, occurring when the remote file has rolled over. (#12913)
* Fix a bug causing an error when options like `--debug` are used without specifying a command. (#13232)
* Improve CTRL-C (cancellation) handling for parallel download threads. (#13234)
* Allow overriding of `CONDA_FETCH_THREADS`/`fetch_threads` to set parallel package downloads beyond the default `5`. (#13263)
* Require `requests >=2.28` for enhanced `response.json()` exception handling. (#13346)
* Apply `callback=reset_context` in `conda.plan` to resolve `conda-build` + `conda-libmamba-solver` incompatibilities. ([conda-libmamba-solver#393](https://github.com/conda/conda-libmamba-solver/issues/393) and [conda-libmamba-solver#386](https://github.com/conda/conda-libmamba-solver/issues/386) via #13357)

### Deprecations

* Deprecate `conda.plugins.subcommands.doctor.health_checks.display_health_checks` function. (#13186)
* Deprecate `conda.plugins.subcommands.doctor.health_checks.display_report_heading` function. (#13186)
* Remove `ruamel_yaml` fallback; use `ruamel.yaml` exclusively. (#13218)
* Deprecate `conda.gateways.anaconda_client.EnvAppDirs` in favor of `platformdirs`. (#13306)
* Mark `conda._vendor.cpuinfo` for pending deprecation. (#13313)
* Deprecate `conda._vendor.distro` in favor of the `distro` package. (#13317)

### Docs

* Add the `conda-sphinx-theme` to the conda documentation. (#13298)
* Update specific pages to remove redundant TOC entries. (#13298)
* Include instructions on updating `conda` in the main `README.md`. (#13343)

### Other

* Add a lighter weight s3 test; update embedded test package index. (#13085)
* Refactor code to use lazy imports for all relative imports in `conda.cli.main_*`, and separate argparse configuration functions from `conda.cli.conda_argparse` to their respective `conda.cli.main_*` modules. (#13173)
* Move custom `argparse.Actions` to `conda.cli.actions` (e.g., `NullCountAction`), and relocate helper argparse functions to `conda.cli.helpers` (e.g., `add_parser_prefix`). (#13173)
* Update upper bound for `ruamel.yaml` to `<0.19` following the release of `0.18`. (#13258)
* Replace `black` with `ruff format` in pre-commit. (#13272)

### Contributors

* @AniketP04 made their first contribution in https://github.com/conda/conda/pull/13224
* @beeankha
* @13rac1 made their first contribution in https://github.com/conda/conda/pull/13191
* @conda-bot
* @dholth
* @eltociear
* @jaimergp
* @jezdez
* @kathatherine
* @kenodegard
* @kennethlaskoski made their first contribution in https://github.com/conda/conda/pull/13322
* @ForgottenProgramme
* @marcoesters
* @opoplawski
* @scruel made their first contribution in https://github.com/conda/conda/pull/13274
* @travishathaway
* @gfggithubleet made their first contribution in https://github.com/conda/conda/pull/13270
* @pre-commit-ci[bot]



## 23.10.0 (2023-10-30)

### ✨ Special announcement ✨

This is an announcement about an important change in conda's functionality:

#### **With this 23.10.0 release we are changing the default solver of conda to [`conda-libmamba-solver`](https://conda.github.io/conda-libmamba-solver/)!** 🥳 🚀

The previously "classic" solver is based on [pycosat](https://github.com/conda/pycosat)/[Picosat](http://fmv.jku.at/picosat/) and will remain part of conda for the foreseeable future, a fallback is possible and available.

#### Why are we switching the solver?

In short: to make conda faster and more accurate.

A "solver" is the core component of most package managers; it calculates which dependencies (and which version of those dependencies) to install when a user requests to install a package from a package repository. To address growth-related challenges within the conda ecosystem, the conda maintainers, alongside partners Anaconda, Quansight and QuantStack, introduced [a new conda dependency solver based on the Mamba project](https://mamba.readthedocs.io) in December 2022.

Since July 2023, the [`conda-libmamba-solver`](https://github.com/conda/conda-libmamba-solver) plugin has been included in all major conda ecosystem installers (miniforge, miniconda, mambaforge and Anaconda Distribution), but was disabled by default. As soon as these installers are updated to contain conda 23.10.0 or later, they will automatically default to using the conda-libmamba-solver plugin.

#### What can I do if this update doesn't work for me?

If the new solver is not working as you expect:

- Check if the behavior you are observing is a [known issue](https://github.com/conda/conda-libmamba-solver/issues/283) or a [deliberate change](https://conda.github.io/conda-libmamba-solver/libmamba-vs-classic/#intentional-deviations-from-classic).
- If that's not the case, please consider submitting a bug report or feature request in the [conda-libmamba-solver repository](https://github.com/conda/conda-libmamba-solver/issues/new/choose).
- If necessary, you can go back to using the `classic` solver without modifying your conda installation:
  - When possible, pass the command line option `--solver=classic` to your `conda` calls.
  - Otherwise (e.g. for `conda build ...` or `constructor ...`), set the environment variable `CONDA_SOLVER=classic`.
  - For permanent changes, use the conda configuration system: `conda config --set solver classic`.

#### Where can I learn more about conda-libmamba-solver?

The documentation of the `conda-libmamba-solver` plugin can be found on [conda.github.io/conda-libmamba-solver](https://conda.github.io/conda-libmamba-solver/).

For more information about the `conda-libmamba-solver` rollout plan, please also see our [blog post from earlier this year](https://conda.org/blog/2023-07-05-conda-libmamba-solver-rollout).

### Enhancements

* Provide `--platform` and `--subdir` flags to create environments for non-native platforms, remembering that choice in future operations. (#11505 via #11794)
* IMPORTANT: Set `solver: libmamba` as the new default solver. (#12984)

### Bug fixes

* Check name of symlink, not its target against valid configuration file names (`condarc`, `.condarc`, or `*.yml/yaml`). (#12956)
* Have `conda doctor` ignore blank lines in `~/.conda/environments.txt`. (#12984)

### Deprecations

* Mark `conda.cli.main.generate_parser` as pending deprecation. Use `conda.cli.conda_argparse.generate_parser` instead. (#13144)
* Mark `conda.auxlib.collection.firstitem` as pending deprecation. (#13144)
* Mark `conda.auxlib.collection.call_each` as pending deprecation. (#13144)
* Mark `conda.auxlib.compat.NoneType` as pending deprecation. (#13144)
* Mark `conda.auxlib.compat.primative_types` as pending deprecation. (#13144)
* Mark `conda.auxlib.compat.utf8_writer` as pending deprecation. (#13144)
* Mark `conda.auxlib.exceptions.AuthenticationError` as pending deprecation. (#13144)
* Mark `conda.auxlib.exceptions.NotFoundError` as pending deprecation. (#13144)
* Mark `conda.auxlib.exceptions.InitializationError` as pending deprecation. (#13144)
* Mark `conda.auxlib.exceptions.SenderError` as pending deprecation. (#13144)
* Mark `conda.auxlib.exceptions.AssignmentError` as pending deprecation. (#13144)
* Mark `conda.auxlib.type_coercion.boolify_truthy_string_ok` as pending deprecation. (#13144)
* Mark `conda.auxlib.type_coercion.listify` as pending deprecation. (#13144)
* Mark `conda.models.dist.IndexRecord` as pending deprecation for removal in 24.9. (#13193)
* Mark `conda.exports.fetch_index` as pending deprecation for removal in 24.9. Use `conda.core.index.fetch_index` instead. (#13194)

### Other

* Constrain minimum conda-build version to `>=3.27`. (#13177)

### Contributors

* @conda-bot
* @dholth
* @jaimergp
* @jezdez
* @kenodegard
* @timhoffm
* @pre-commit-ci[bot]



## 23.9.0 (2023-09-27)

### Special announcement

This is an announcement about an important and positive future change in conda's functionality:

> We will change the default solver of conda to [`conda-libmamba-solver`](https://conda.github.io/conda-libmamba-solver/) in a __special 23.10.0 release__ in the near future!

You can already benefit from it _today_ by [configuring your conda installation to use it](https://conda.github.io/conda-libmamba-solver/getting-started/#usage) (e.g. by running `conda config --set solver libmamba`).

The current "classic" solver is based on [pycosat](https://github.com/conda/pycosat)/[Picosat](http://fmv.jku.at/picosat/) and will remain part of conda for the foreseeable future, a fallback is possible and available (see below).

#### Plan to change the default solver

Here is our updated plan to change the default solver, to better follow [CEP 8](https://github.com/conda-incubator/ceps/blob/main/cep-8.md) and reduce the potential impact on conda users:

- The upcoming, special 23.10.0 release will be dedicated to the switch of the default solver to `libmamba`.
- Users will be able to opt out of the `libmamba` solver and use the `classic` solver instead, by using one of these options:
  - the `--solver=classic` command line option,
  - the `CONDA_SOLVER=classic` environment variable or
  - running `conda config --set solver classic`.
- All development of `conda-libmamba-solver` plugin happens in the [conda-libmamba-solver repo](https://github.com/conda/conda-libmamba-solver), including issue tracking.
- The documentation of the `conda-libmamba-solver` plugin can be found on [conda.github.io/conda-libmamba-solver](https://conda.github.io/conda-libmamba-solver/).

For more information about the `conda-libmamba-solver` rollout plan, please also see our [blog post from earlier this year](https://conda.org/blog/2023-07-05-conda-libmamba-solver-rollout).

#### Context

A "solver" is the core component of most package managers; it calculates which dependencies (and which version of those dependencies) to install when a user requests to install a package from a package repository. To address growth-related challenges within the conda ecosystem, the conda maintainers, alongside partners Anaconda, Quansight and QuantStack, introduced [a new conda dependency solver based on the Mamba project](https://mamba.readthedocs.io) in December 2022.

Since July 2023, that [`conda-libmamba-solver`](https://github.com/conda/conda-libmamba-solver) plugin has been included in and automatically installed with all major conda ecosystem installers (miniforge, miniconda, mambaforge and Anaconda Distribution), _with the default solver configuration unchanged_.

### Enhancements

* Improve speed of `fish` shell initialization. (#12811)
* Directly suppress use of binstar (conda) token when fetching trust metadata. (#12889)
* Add a new "auth handler" plugin hook for conda. (#12911)
* Lock index cache metadata by default. Added `--no-lock` option in case of
  problems, should not be necessary. Older `--experimental=lock` no longer has
  an effect. (#12920)
* Add `context.register_envs` option to control whether to register environments
  in `~/.conda/environments.txt` when they are created. Defaults to true. (#12924)
* Inject a new detailed output verbosity level (i.e., the old debug level `-vv` is now `-vvv`). (#12985, #12977, #12420, #13036)
* Add support for `truststore` to the `ssl_verify` config option, enabling conda to use the operating system certificate store (requires Python 3.10 or later). (#13075 and #13149)
* Add `emscripten-wasm32` and `wasi-wasm32` platforms to known platforms. (#13095)
* Adds the `py.typed` marker file to the `conda` package for compliance with PEP-561. (#13107)
* Import `boto3` only when S3 channels are used, saving startup time. (#12914)

### Bug fixes

* When using pip dependencies with `conda env create`, check the directory permissions before writing to disk. (#11610)
* Hide `InsecureRequestWarning` for JLAP when `CONDA_SSL_VERIFY=false`, matching
  non-JLAP behavior. (#12731)
* Disallow ability to create a conda environment with a colon in the prefix. (#13044)
* Fix `AttributeError` logging response with nonexistent request when using JLAP
  with `file:///` URIs. (#12966)
* Do not show progress bars in non-interactive runs for cleaner logs. (#12982)
* Fix S3 bucket name. (#12989)
* Default `--json` and `--debug` to `NULL` so as to not override `CONDA_JSON` and `CONDA_DEBUG` environment variables. (#12987)
* ``XonshActivator`` now uses ``source-bash`` in non-interactive mode to avoid
  side-effects from interactively loaded RC files. (#13012)
* Fix `conda remove --all --json` output. (#13019)
* Update test data to stop triggering security scanners' false-positives. (#13034)
* Fix performance regression of basic commands (e.g., `conda info`) on WSL. (#13035)
* Configure conda to ignore "Retry-After" header to avoid the scenarios when this value is very large and causes conda to hang indefinitely. (#13050)
* Treat `JSONDecodeError` on `repodata.info.json` as a warning, equivalent to a
  missing `repodata.info.json`. (#13056)
* Fix sorting error for `conda config --show-sources --json`. (#13076)
* Catch `OSError` in `find_commands` to account for incorrect `PATH` entries on
  Windows. (#13125)
* Catch a `NotWritableError` when trying to find the first writable package cache dir. (#9609)
* `conda env update --prune` uses only the specs coming from `environment.yml` file and ignores the history specs. (#9614)

### Deprecations

* Removed `conda.another_unicode()`. (#12948)
* Removed `conda._vendor.toolz`. (#12948, #13141)
* Removed `conda._vendor.tqdm`. (#12948)
* Removed `conda.auxlib.decorators.memoized` decorator. (#12948)
* Removed `conda.base.context.Context.experimental_solver`. (#12948)
* Removed `conda.base.context.Context.conda_private`. (#12948)
* Removed `conda.base.context.Context.cuda_version`. (#12948)
* Removed `conda.base.context.get_prefix()`. (#12948)
* Removed `conda.cli.common.ensure_name_or_prefix()`. (#12948)
* Removed `--experimental-solver` command line option. (#12948)
* Removed `conda.common.cuda` module. (#12948)
* Removed `conda.common.path.explode_directories(already_split)`. (#12948)
* Removed `conda.common.url.escape_channel_url()`. (#12948)
* Removed `conda.core.index.check_whitelist()`. (#12948)
* Removed `conda.core.solve._get_solver_class()`. (#12948)
* Removed `conda.core.subdir_data.read_mod_and_etag()`. (#12948)
* Removed `conda.gateways.repodata.RepodataState.load()`. (#12948)
* Removed `conda.gateways.repodata.RepodataState.save()`. (#12948)
* Removed `conda.lock` module. (#12948)
* Removed `conda_env.cli.common.stdout_json()`. (#12948)
* Removed `conda_env.cli.common.get_prefix()`. (#12948)
* Removed `conda_env.cli.common.find_prefix_name()`. (#12948)
* Remove import of deprecated cgi module by deprecating ftp STOR support.
  (#13013)
* Require `boto3` for S3 support and drop support for the older `boto` as it
  doesn't support our minimum required version of Python. (#13112)
* Reduce startup delay from deprecations module by using `sys._getframe()`
  instead of `inspect.stack()`. (#12919)

### Other

* Use Ruff linter in pre-commit configuration (#12279)
* Remove unused `cache_path` arguments from `RepoInterface`/`JlapRepoInterface`;
  replaced by cache object. (#12927)

### Contributors

* @beenje
* @beeankha
* @chbrandt
* @chenghlee
* @conda-bot
* @dbast
* @dholth
* @duncanmmacleod
* @gforsyth
* @eltociear
* @jaimergp
* @jezdez
* @jmcarpenter2 made their first contribution in https://github.com/conda/conda/pull/13034
* @kenodegard
* @ForgottenProgramme
* @Mon-ius made their first contribution in https://github.com/conda/conda/pull/12811
* @otaithleigh made their first contribution in https://github.com/conda/conda/pull/13035
* @psteyer made their first contribution in https://github.com/conda/conda/pull/11610
* @tarcisioe made their first contribution in https://github.com/conda/conda/pull/9614
* @travishathaway
* @wolfv made their first contribution in https://github.com/conda/conda/pull/13095
* @zeehio made their first contribution in https://github.com/conda/conda/pull/13075
* @pre-commit-ci[bot]



## 23.7.4 (2023-09-12)

### Enhancements

* Use `os.scandir()` to find conda subcommands without `stat()` overhead. (#13033, #13067)

### Bug fixes

* Fix S3 bucket name in test suite. (#12989)
* Fix performance regression of basic commands (e.g., `conda info`) on WSL. (#13035)
* Catch `PermissionError` raised by `conda.cli.find_commands.find_commands` when user's `$PATH` contains restricted paths. (#13062, #13089)
* Fix sorting error for `conda config --show-sources --json`. (#13076)

### Contributors

* @beeankha
* @dholth
* @kenodegard
* @otaithleigh made their first contribution in https://github.com/conda/conda/pull/13035


## 23.7.3 (2023-08-21)

### Bug fixes

* Fix regression for supporting conda executable plugins installed into non-base environments. (#13006)

### Contributors

* @kenodegard



## 23.7.2 (2023-07-27)

### Bug fixes

* Fix regression in parsing `--json` and `--debug` flags for executable plugins. (#12935, #12936)

### Contributors

* @kenodegard



## 23.7.1 (2023-07-26)

### Bug fixes

* Patch parsed args with pre_args to correctly parse `--json` and `--debug` arguments. (#12928, #12929)

### Contributors

* @jezdez
* @kenodegard



## 23.7.0 (2023-07-25)

### Enhancements

* Add `conda.deprecations.DeprecationHandler.action` helper to deprecate `argparse.Action`s. (#12493)
* Add support for the FreeBSD operating system and register `freebsd-64` as a known subdirectory for FreeBSD on x86-64. (#12647)
* Do not mock `$CONDA_PREFIX` when `--name` or `--prefix` is provided. (#12696)
* Add support for `sha256` filters in the MatchSpec syntax (e.g. `*[sha256=f453db4ffe2271ec492a2913af4e61d4a6c118201f07de757df0eff769b65d2e]`). (#12654 via #12707)
* Add a new health check to `conda doctor` detecting altered packages in an environment by comparing expected and computed `sha256` checksums. (#12757)
* Add new `pre_commands` and `post_commands` plugin hooks allowing plugins to run code before and after `conda` subcommands. (#12712, #12758, #12864)
* Stop using `distutils` directly in favor of the vendored version in `setuptools` 60 and later or standard library equivalents. (#11136)
* Add a `CITATION.cff` file to the root of the repository to make it easier for users to cite conda. (#12781)
* Add optional `CondaSubcommand.configure_parser` allowing third-party plugins to hook into conda's argument parser. (#12814)
* Only display third-party subcommands in `conda --help` and not for every other subcommand. (#12814, #12740)
* Add a new config option, `no_plugins`, a` --no-plugins` command line flag, and a `CONDA_NO_PLUGINS` environment variable that disables external plugins for built-in conda commands. (#12748)
* Register plugins using their canonical/fully-qualified name instead of the easily spoofable entry point name. (#12869)
* De-duplicate plugin and legacy subcommands in `conda --help`. (#12893)
* Implement a 2-phase parser to better handle plugin disabling (via `--no-plugins`). (#12910)
* Refactor subcommand parsing to use a greedy parser since `argparse.REMAINDER` has [known issues](https://github.com/python/cpython/issues/61252). (#12910)

### Bug fixes

* Use `requests.exceptions.JSONDecodeError` for ensuring compatibility with different `json` implementations used by requests. This fixes a bug that caused only the first of multiple given source URLs to be tried. This also raises the minimum required requests version to 2.27.0. (#12683)
* Don't export `__osx` virtual package when `CONDA_OVERRIDE_OSX=""`. (#12715)
* Fix erroneous `conda deactivate` behavior of unsetting preexisting environment variables that are identical to those set during `conda activate`. (#12769)
* Correct third-party subcommands to receive _remaining_ arguments instead of a blanket `sys.argv[2:]` which broke `conda_cli` testing. (#12814, #12910)

### Deprecations

* Mark `conda.base.context.context.root_dir` as pending deprecation. Use `conda.base.context.context.root_prefix` instead. (#12701)
* Mark `conda.plugins.subcommands.doctor.cli.get_prefix` as pending deprecation. Use `conda.base.context.context.target_prefix` instead. (#12725)
* Mark `conda.models.leased_path_entry.LeasedPathEntry` as pending deprecation. (#12735)
* Mark `conda.models.enums.LeasedPathType` as pending deprecation. (#12735)
* Mark `conda.common.temporary_content_in_file` as pending deprecation. Use `tempfile` instead. (#12795)
* Mark `conda.cli.python_api` as pending deprecation. Use `conda.testing.conda_cli` fixture instead. (#12796)

### Docs

* Document how to use the new `pre_commands` and `post_commands` plugin hooks. (#12712, #12758)
* Add docstrings to all public modules. (#12792)
* Auto-generate API docs using `sphinx-autoapi`. (#12798)
* Convert all manual redirects into config using `sphinx-reredirects`. (#12798)
* Revise the plugins index page to make it easier to understand how to create a conda plugin. (#12802)
* Add missing `conda env` CLI docs. (#12841)

### Other

* Update `tests/cli/test_main_rename.py` to use latest fixtures. (#12517)
* Update `tests/test_activate.py` to test the new behavior. (#12769)
* Re-enable all `conda_env` tests and remove irrelevant tests. (#12813)
* Convert all `unittest`-style tests to `pytest`-style. (#12819)
* Convert `tests/test-recipes` into local noarch packages instead of relying on conda-test channel and local builds. (#12879)

### Contributors

* @beeankha
* @conda-bot
* @dariocurr
* @jaimergp
* @jezdez
* @johanneskoester made their first contribution in https://github.com/conda/conda/pull/12683
* @jjhelmus
* @kalawac made their first contribution in https://github.com/conda/conda/pull/12738
* @kenodegard
* @schackartk made their first contribution in https://github.com/conda/conda/pull/12781
* @lesteve made their first contribution in https://github.com/conda/conda/pull/12715
* @ForgottenProgramme
* @marcoesters made their first contribution in https://github.com/conda/conda/pull/12863
* @mpotane made their first contribution in https://github.com/conda/conda/pull/11740
* @mattkram made their first contribution in https://github.com/conda/conda/pull/12730
* @morremeyer made their first contribution in https://github.com/conda/conda/pull/12871
* @mcg1969
* @travishathaway
* @pre-commit-ci[bot]



## 23.5.2 (2023-07-13)

### Bug fixes

* Correct `native_path_to_unix` failure to handle no paths (e.g., an empty string or an empty iterable). (#12880)

### Contributors

* @kenodegard



## 23.5.1 (2023-07-12)

### Bug fixes

* Add (back) the `cygpath` fallback logic since `cygpath` is not always available on Windows. (#12873)

### Contributors

* @kenodegard



## 23.5.0 (2023-05-17)

### Enhancements

* Add `conda doctor` subcommand plugin. (#474)
* Add Python 3.11 support. (#12256)
* Add `conda list --reverse` to return a reversed list of installed packages. (#11954)
* Switch from `setup.py` to `pyproject.toml` and use [Hatchling](https://pypi.org/project/hatchling/) for our build system. (#12509)
* Optimize which Python modules get imported during `conda activate` calls to make it faster. (#12550)
* Add `conda_cli` fixture to replace `conda.testing.helpers.run_inprocess_conda_command` and `conda.testing.integration.run_command`. (#12592)
* Add `tmp_env` fixture to replace `conda.testing.integration.make_temp_env`. (#12592)
* Add `path_factory` fixture to replace custom prefix logic like `conda.testing.integration._get_temp_prefix` and `conda.testing.integration.make_temp_prefix`. (#12592)
* Refactor the way that the `Activator` classes are defined in `conda/activate.py`. (#12627)
* Warn about misconfiguration when signature verification is enabled. (#12639)

### Bug fixes

* `conda clean` no longer fails if we failed to get the file stats. (#12536)
* Provide fallback version if `conda.deprecations.DeprecationHandler` receives a bad version. (#12541)
* Ensure the default value for `defaults` includes `msys2` when `context.subdir` is `win-*` on non-Windows platforms. (#12555)
* Avoid `TypeError` when non-string types are written to the index cache metadata. (#12562)
* `conda.core.package_cache_data.UrlsData.get_url` no longer fails when `package_path` has `.conda` extension. (#12516)
* Stop pre-converting paths to Unix style on Windows in `conda.sh`, so that they are prefix replaceable upon installation, which got broken by #12509. It also relies on `cygpath` at runtime, which all `msys2`/`cygwin` bash versions on Windows should have available. (#12627)

### Deprecations

* Mark `conda_env.pip_util.get_pip_version` as pending deprecation. (#12492)
* Mark `conda_env.pip_util.PipPackage` as pending deprecation. (#12492)
* Mark `conda_env.pip_util.installed` as pending deprecation. (#12492)
* Mark `conda_env.pip_util._canonicalize_name` as pending deprecation. (#12492)
* Mark `conda_env.pip_util.add_pip_installed` as pending deprecation. (#12492)
* Mark `conda_env.env.load_from_directory` as pending deprecation. (#12492)
* Mark `python -m conda_env.cli.main` as pending deprecation. Use `conda env` instead. (#12492)
* Mark `python -m conda_env` as pending deprecation. Use `conda env` instead. (#12492)
* Mark `conda.auxlib.packaging` for deprecation in 24.3.0. (#12509)
* Rename index cache metadata file `.state.json` to `.info.json` to track draft CEP. (#12669)
* Mark `conda.testing.integration.get_conda_list_tuple` as pending deprecation. Use `conda.core.prefix_data.PrefixData().get()` instead. (#12676)
* Mark `conda.testing.encode_for_env_var` as pending deprecation. (#12677)
* Mark `conda.testing.integration.temp_chdir` as pending deprecation. Use `monkeypatch.chdir` instead. (#12678)

### Docs

* Change the README example from IPython Notebook and NumPy to PyTorch. (#12579)
* Discuss options available to properly configure mirrored channels. (#12583, #12641)
* Add `flake8-docstrings` to `pre-commit`. (#12620)

### Other

* Update retry language in flexible solve and `repodata` logs to be less ominous. (#12612)
* Improve `repodata` / `subdir_data` programming interface (#12521). Index cache metadata has changed to `.info.json` to better align with the [draft CEP](https://github.com/conda-incubator/ceps/pull/48). Improve cache locking when using `jlap`. Improve `jlap` logging. (#12572)
* Format with `black` and replaced `pre-commit`'s `darker` hook with `black`. (#12554)
* Format with `isort` and add `pre-commit` `isort` hook. (#12554)
* Add functional tests around conda's content trust code. (#11805)
* Enable `flake8` checks that are now handled by `black`. (#12620)

### Contributors

* @beeankha
* @chbrandt made their first contribution in https://github.com/conda/conda/pull/12419
* @chenghlee
* @conda-bot
* @dholth
* @THEdavehogue made their first contribution in https://github.com/conda/conda/pull/12612
* @HeavenEvolved made their first contribution in https://github.com/conda/conda/pull/12496
* @eltociear
* @jaimergp
* @jezdez
* @johnnynunez made their first contribution in https://github.com/conda/conda/pull/12256
* @kenodegard
* @ForgottenProgramme
* @pkmooreanaconda
* @tl-hbk made their first contribution in https://github.com/conda/conda/pull/12604
* @vic-ma made their first contribution in https://github.com/conda/conda/pull/12579
* @pre-commit-ci[bot]
* @sausagenoods made their first contribution in https://github.com/conda/conda/pull/12631



## 23.3.1 (2023-03-28)

### Enhancements

* Fix and re-enable binstar tests. Replace custom property caching with `functools.cached_property`. (#12495)

### Bug fixes

* Restore default argument for `SubdirData` method used by `conda-index`. (#12513)
* Include `conda.gateways.repodata.jlap` submodule in package. (#12545)

### Other

* Add linux-s390x to multi-arch ci/dev container. (#12498)
* Expose a `MINIO_RELEASE` environment variable to provide a way to pin `minio` versions in CI setup scripts. (#12525)
* Add `jsonpatch` dependency to support `--experimental=jlap` feature. (#12528)

### Contributors

* @conda-bot
* @dbast
* @dholth
* @jaimergp
* @kenodegard
* @ForgottenProgramme



## 23.3.0 (2023-03-14)

### Enhancements

* Allow the use of environment variables for channel urls in `environment.yaml`. (#10018)
* Improved error message for `conda env create` if the environment file is missing. (#11883)
* Stop using `toolz.dicttoolz.merge` and `toolz.dicttoolz.merge_with`. (#12039)
* Add support for incremental `repodata.json` updates with `--experimental=jlap` on the command line or `experimental: ["jlap"]` in `.condarc` (#12090). Note: switching between "use jlap" and "don't use jlap" invalidates the cache.
* Added a new `conda.deprecations` module for easier & standardized deprecation. Includes decorators to mark functions, modules, classes, and arguments for deprecation and functions to mark modules, constants, and topics for deprecation.  (#12125)
* Adds a new `channel_settings` configuration parameter that will be used to override arbitrary settings on per-channel basis. (#12239)
* Improve speed of `repodata.json` parsing by deferring creation of individual `PackageRecord` objects. (#8500)
* Refactor subcommand argument parsing to make it easier to understand. This calls the plugin before invoking the default argument parsing. (#12285)
* Handle I/O errors raised while retrieving channel notices. (#12312)
* Add support for the 64-bit RISC-V architecture on Linux. (#12319)
* Update vendored version of `py-cpuinfo` to 0.9.0. (#12319)
* Improved code coverage. (#12346, #12457, #12469)
* Add a note about `use_only_tar_bz2` being enabled on `PackagesNotFoundError` exceptions. (#12353)
* Added to conda CLI help that `conda remove -n <myenv> --all` can be used to delete environments. (#12378)
* Handle Python import errors gracefully when loading conda plugins from entrypoints. (#12460)

### Bug fixes

* Fixed errors when renaming without an active environment. (#11915)
* Prevent double solve attempt if `PackagesNotFoundError` is raised. (#12201)
* Virtual packages follow `context.subdir` instead of `platform.system()` to enable cross-platform installations. (#12219)
* Don't export `__glibc` virtual package when `CONDA_OVERRIDE_GLIBC=""`. (#12267)
* Fix `arg_parse` pass-through for `--version` and `--help` in `conda.xsh`. (#12344)
* Filter out `None` path values from `pwd.getpwall()` on Unix systems, for users without home directories, when running as root. (#12063)
* Catch `ChunkedEncodingError` exceptions to prevent network error tracebacks hitting the output. (#12196 via #12487)
* Fix race conditions in `mkdir_p_sudo_safe`. (#12490)

### Deprecations

* Drop `toolz.itertoolz.unique` in favor of custom `conda.common.iterators.unique` implementation. (#12252)
* Stop using `OrderedDict`/`odict` since `dict` preserves insert order since Python 3.7. (#12254)
* Mark `conda._vendor.boltons` for deprecation in 23.9.0. (#12272, #12482)
* Mark `conda_exe` in `context.py` and a topic in `print_package_info` `cli/main_info.py` for official deprecation. (#12398)
* Remove unused `chain`, `methodcaller`, `mkdtemp`, `StringIO` imports in `conda.common.compat`; apply other fixes from `ruff --fix .` in the test suite. (#12294)
* Remove unused optimization for searching packages based on `*[track_features=<feature name>]`. (#12314)
* Remove Notebook spec support from `conda env`; this was deprecated already and scheduled to be remove in version 4.5. (#12307)
* Mark `conda_exe` in `context.py` and a topic in `print_package_info` `cli/main_info.py` for official deprecation. (#12276)
* Marking `conda.utils.hashsum_file` as pending deprecation. Use `conda.gateways.disk.read.compute_sum` instead. (#12414)
* Marking `conda.utils.md5_file` as pending deprecation. Use `conda.gateways.disk.read.compute_sum(path, "md5")` instead. (#12414)
* Marking `conda.gateways.disk.read.compute_md5sum` as pending deprecation. Use `conda.gateways.disk.read.compute_sum(path, "md5")` instead. (#12414)
* Marking `conda.gateways.disk.read.compute_sha256sum` as pending deprecation. Use `conda.gateways.disk.read.compute_sum(path, "sha256")` instead. (#12414)
* Drop Python 3.7 support. (#12436)

### Docs

* Added docs for `conda.deprecations`. (#12452)
* Updated some instances of "Anaconda Cloud" to be "Anaconda.org". (#12238)
* Added documentation on the specifications for `conda search` and `conda install`. (#12304)
* Mark `conda.utils.safe_open` for deprecation. Use builtin `open` instead. (#12415)

### Other

* Update `<cache key>.json.state` `repodata.json` cache format; check `mtime` against cached `repodata.json`. (#12090)
* Skip redundant `tar --no-same-owner` when running as root on Linux, since newer `conda-package-handling` avoids setting ownership from the archive. (#12231)
* Add additional extensions to `conda.common.path` for future use. (#12261)
* Pass `--cov` in test runner scripts but not in `setup.cfg` defaults, for easier debugging. (#12268)
* Constrain conda-build to at least >=3.18.3, released 2019-06-20. (#12309)
* Improve `start.bat` Windows development script. (#12311)
* Provide conda-forge-based Docker images and fix the bundled `minio` binary. (#12335)
* Add support for conda-forge-based CI runtimes. On Linux (all architectures), unit & integration tests will use Python 3.10. On Windows, Python 3.8. On macOS, only the unit tests are run with conda-forge (_instead_ of `defaults`!), using Python 3.9. (#12350, #12447 via #12448)
* Fix testing data issue where the `subdir` entry in some files was mismatched. (#12389)
* Initialize conda after installing test requirements during CI. (#12446)
* Speedup pre-commit by a factor of 15 by removing ignored hooks (`pylint`/`bandit`). This locally reduces the pre-commit runtime from ~43sec to 2.9sec and thus makes it possible to run pre-commit in a loop during development to constantly provide feedback and style the code. (#12466)

### Contributors

* @AdrianFreundQC made their first contribution in https://github.com/conda/conda/pull/11883
* @sanzoghenzo made their first contribution in https://github.com/conda/conda/pull/12074
* @beeankha
* @conda-bot
* @dbast
* @dholth
* @FelisNivalis made their first contribution in https://github.com/conda/conda/pull/11915
* @gforsyth made their first contribution in https://github.com/conda/conda/pull/12344
* @eltociear made their first contribution in https://github.com/conda/conda/pull/12377
* @jaimergp
* @jezdez
* @jjhelmus
* @kannanjayachandran made their first contribution in https://github.com/conda/conda/pull/12363
* @kathatherine
* @kenodegard
* @ForgottenProgramme
* @ryanskeith made their first contribution in https://github.com/conda/conda/pull/12439
* @31Sanskrati made their first contribution in https://github.com/conda/conda/pull/12371
* @travishathaway
* @pre-commit-ci[bot]



## 23.1.0 (2023-01-17)

### Bug fixes

* Detect CUDA driver version in subprocess. (#11667)
* Fixes the behavior of the `--no-user` flag in `conda init` so that a user's `.bashrc`, etc. remains unaltered, as expected. (#11949)
* Fix several more user facing `MatchSpec` crashes that were identified by fuzzing efforts. (#12099)
* Lock `sys.stdout` to avoid corrupted `--json` multithreaded download progress. (#12231)

### Docs

* Optional Bash completion support has been removed starting in v4.4.0, and not just deprecated. (#11171)
* Documented optional `channel::package` syntax for specifying dependencies in `environment.yml` files. (#11890)

### Other

* Refactor `repodata.json` fetching; update on-disk cache format. Based on work by @FFY00. (#11600)
* Environment variable overwriting WARNING is printed only if the env vars are different from those specified in the OS. (#12128)
* Added `conda-libmamba-solver` run constraint. (#12156)
* Updated `ruamel.yaml` version. (#12156)
* Added `tqdm` dependency. (#12191)
* Use `itertools.chain.from_iterable` instead of equivalent `tlz.concat`. (#12165)
* Use `toolz.unique` instead of vendored copy. (#12165)
* Use `itertools.islice` instead of `toolz.take`. (#12165)
* Update CI test workflow to only run test suite when code changes occur. (#12180)
* Added Python 3.10 canary builds. (#12184)

### Contributors

* @beeankha
* @dholth
* @dariocurr made their first contribution in https://github.com/conda/conda/pull/12128
* @FFY00 made their first contribution in https://github.com/conda/conda/pull/11600
* @jezdez
* @jay-tau made their first contribution in https://github.com/conda/conda/pull/11738
* @kenodegard
* @pkmooreanaconda
* @sven6002 made their first contribution in https://github.com/conda/conda/pull/12162
* @ReveStobinson made their first contribution in https://github.com/conda/conda/pull/12213
* @travishathaway
* @XuehaiPan made their first contribution in https://github.com/conda/conda/pull/11667
* @xylar made their first contribution in https://github.com/conda/conda/pull/11949
* @pre-commit-ci[bot]



## 22.11.1 (2022-12-06)

### Bug fixes

* Restore default virtual package specs as in 22.9.0 (#12148)
  - re-add `__unix`/`__win` packages
  - restore `__archspec` version/build string composition

### Other

* Skip test suite for non-code changes. (#12141)

### Contributors

* @LtDan33
* @jezdez
* @kenodegard
* @mbargull
* @travishathaway

## 22.11.0 (2022-11-23)

### Enhancements

* Add LD_PRELOAD to env variable list. (#10665)
* Improve CLI warning about updating conda. (#11300)
* Conda's initialize block in the user's profiles will check whether the conda executable exists before calling the conda hook. (#11374)
* Switch to `tqdm` as a real dependency. (#12005)
* Add a new plugin mechanism. (#11435)
* Add an informative message if explicit install fails due to requested packages not being in the cache. (#11591)
* Download and extract packages in parallel. Greatly speeds up package downloads when latency is high. Controlled by the new `fetch_threads` config parameter, defaulting to 5 parallel downloads. Thanks @shuges-uk for reporting. (#11841)
* Add a new plugin hook for virtual packages and convert existing code for virtual packages (from index.py) into plugins. (#11854)
* Require `ruamel.yaml`. (#11868, #11837)
* Stop using `toolz.accumulate`. (#12020)
* Stop using `toolz.groupby`. (#11913)
* Remove vendored `six` package. (#11979)
* Add the ability to extend the solver backends with the ``conda_solvers`` plugin hook. (#11993)
* Stop using `toolz.functoolz.excepts`. (#12016)
* Stop using `toolz.itertoolz.concatv`. (#12020)
* Also try UTF16 and UTF32 encodings when replacing the prefix. (#9946)

### Bug fixes

* `conda env update` would ask for user input and hang when working with pip installs of git repos and the repo was previously checked out. Tell pip not to ask for user input for that case.  (#11818)
* Fix for `conda update` and `conda install` issues related to channel notices. (#11852)
* Signature verification printed `None` when disabled, changes default `metadata_signature_status` to an empty string instead. (#11944)
* Fix importlib warnings when importing conda.cli.python_api on python=3.10. (#11975)
* Several user facing MatchSpec crashes were identified by fuzzing efforts. (#11999)
* Apply minimal fixes to deal with these (and similar) crashes. (#12014)
* Prevent `conda` from using `/bin/sh` + `exec` trick for its own entry point, which drops `$PS1` on some shells (#11885, #11893 via #12043).
* Handle `CTRL+C` during package downloading more gracefully. (#12056)
* Prefer the outer name when a MatchSpec specifies a package's name twice package-name[name=package-name] (#12062)

### Deprecations

* Add a pending deprecation warning for when importing `tqdm` from `conda._vendor`. (#12005)
* Drop `ruamel_yaml` and `ruamel_yaml_conda` in favor of `ruamel.yaml`. (#11837)
* `context.experimental_solver` is now marked for pending deprecation. It is replaced by `context.solver`. The same applies to the `--experimental-solver` flag, the `CONDA_EXPERIMENTAL_SOLVER` environment variable, and the `ExperimentalSolverChoice` enum, which will be replaced by `--solver`, `EXPERIMENTAL_SOLVER` and `SolverChoice`, respectively. (#11889)
* Mark `context.conda_private` as pending deprecation. (#12101)

### Docs

* Add corresponding documentation for the new plugins mechanism. (#11435)
* Update conda cheatsheet for the 4.14.0 release. The cheatsheet now includes an example for `conda rename`. (#11768)
* Document conda-build package format v2, also known as the `.conda`-format. (#11881)
* Remove `allow_other_channels` config option from documentation, as the option no longer exists. (#11866)
* Fix bad URL to "Introduction to conda for Data Scientists" course in conda docs. (#9782)

### Other

* Add a comment to the code that explains why .bashrc is modified on Linux and .bash_profile is modified on Windows/macOS when executing `conda init`. (#11849)
* Add `--mach` and `--arch` options to `dev/start`. (#11851)
* Remove encoding pragma in file headers, as it's not needed in Python 3 anymore. (#11880)
* Refactor `conda init SHELLS` as argparse choices. (#11897)
* Drop pragma fixes from pre-commit checks. (#11909)
* Add pyupgrade to pre-commit checks. This change affects many files. Existing pull requests may need to be updated, rebased, or merged to address conflicts. (#11909)
* Add aarch64 and ppc64le as additional CI platforms for smoke testing. (#11911)
* Serve package files needed for testing using local server. (#12024)
* Update canary builds to guarantee builds for the commits that trigger workflow. (#12040)

### Contributors

* @arq0017 made their first contribution in https://github.com/conda/conda/pull/11810
* @beeankha
* @conda-bot
* @dbast
* @dholth
* @erykoff
* @consideRatio made their first contribution in https://github.com/conda/conda/pull/12028
* @jaimergp
* @jezdez
* @kathatherine
* @kenodegard
* @ForgottenProgramme made their first contribution in https://github.com/conda/conda/pull/11926
* @hmaarrfk made their first contribution in https://github.com/conda/conda/pull/9946
* @NikhilRaverkar made their first contribution in https://github.com/conda/conda/pull/11842
* @pavelzw made their first contribution in https://github.com/conda/conda/pull/11849
* @pkmooreanaconda made their first contribution in https://github.com/conda/conda/pull/12014
* @fragmede made their first contribution in https://github.com/conda/conda/pull/11818
* @SatyamVyas04 made their first contribution in https://github.com/conda/conda/pull/11870
* @timhoffm
* @travishathaway
* @dependabot made their first contribution in https://github.com/conda/conda/pull/11965
* @pre-commit-ci[bot]
* @wulmer


## 22.9.0 (2022-09-14)

### Special announcement

If you have been following the conda project previously, you will notice a change in our version number for this release. We have officially switched to the [CalVer](https://calver.org/) versioning system as agreed upon in [CEP 8](https://github.com/conda-incubator/ceps/blob/main/cep-8.md) (Conda Enhancement Proposal).

Please read that CEP for more information, but here is a quick synopsis. We hope that this versioning system and our release schedule will help make our releases more predictable and transparent to the community going forward. We are now committed to making at least one release every two months, but keep in mind that we can (and most likely will) be making minor version releases within this window.

### Enhancements

* Replace vendored toolz with toolz dependency. (#11589, #11700)
* Update bundled Python launchers for Windows (`conda/shell/cli-*.exe`) to match the ones found in conda-build. (#11676)
* Add `win-arm64` as a known platform (subdir). (#11778)

### Bug fixes

* Remove extra prefix injection related to the shell interface breaking `conda run`. (#11666)
* Better support for shebang instructions in prefixes with spaces. (#11676)
* Fix `noarch` entry points in Unicode-containing prefixes on Windows. (#11694)
* Ensure that exceptions that are raised show up properly instead of resulting in a blank `[y/N]` prompt. (#11746)

### Deprecations

* Mark `conda._vendor.toolz` as pending deprecation. (#11704)
* Removes vendored version of urllib3. (#11705)

### Docs

* Added conda capitalization standards to CONTRIBUTING file. (#11712)

### Other

* Add arm64 support to development script `. ./dev/start`. (#11752)
* Update canary-release version to resolve canary build issue. (#11761)
* Renamed canary recipe from `conda.recipe` to `recipe`. (#11774)

### Contributors

* @beeankha
* @chenghlee
* @conda-bot
* @dholth
* @isuruf
* @jaimergp
* @jezdez
* @razzlestorm made their first contribution in https://github.com/conda/conda/pull/11736
* @jakirkham
* @kathatherine
* @kenodegard
* @scdub made their first contribution in https://github.com/conda/conda/pull/11816
* @travishathaway
* @pre-commit-ci[bot]


## 4.14.0 (2022-08-02)

### Enhancements

* Only star activated environment in `conda info --envs`/`conda env list`. (#10764)
* Adds new sub-command, `conda notices`, for retrieving channel notices. (#11462)
* Notices will be intermittently shown after running, `install`, `create`, `update`, `env create` or `env update`. New notices will only be shown once. (#11462)
* Implementation of a new `rename` subcommand. (#11496)
* Split `SSLError` from `HTTPError` to help resolve HTTP 000 errors. (#11564)
* Include the invalid package name in the error message. (#11601)
* Bump requests version (`>=2.20.1`) and drop monkeypatching. (#11643)
* Rename `whitelist_channels` to `allowlist_channels`. (#11647)
* Always mention channel when notifying about a new conda update. (#11671)

### Bug fixes


* Correct a misleading `conda --help` error message. (#11625)
* Fix support for CUDA version detection on WSL2. (#11626)
* Fixed the bug when providing empty environment.yml to `conda env create` command. (#11556, #11630)
* Fix MD5 hash generation for FIPS-enabled systems. (#11658)
* Fixed `TypeError` encountered when logging is set to DEBUG and the package's JSON cannot be read. (#11679)

### Deprecations


* `conda.cli.common.ensure_name_or_prefix` is pending deprecation in a future release. (#11490)
* Mark `conda.lock` as pending deprecation. (#11571)
* Remove lgtm.com config. (#11572)
* Remove Python 2.7 `conda.common.url.is_ipv6_address_win_py27` implementation. (#11573)
* Remove redundant `conda.resolve.dashlist` definition. (#11578)
* Mark `conda_env.cli.common.get_prefix` and `conda.base.context.get_prefix` as pending deprecation in favor of `conda.base.context.determine_target_prefix`. (#11594)
* Mark `conda_env.cli.common.stdout_json` as pending deprecation in favor of `conda.cli.common.stdout_json`. (#11595)
* Mark `conda_env.cli.common.find_prefix_name` as pending deprecation. (#11596)
* Mark `conda.auxlib.decorators.memoize` as pending deprecation in favor of `functools.lru_cache`. (#11597)
* Mark `conda.exports.memoized` as pending deprecation in favor of `functools.lru_cache`. (#11597)
* Mark `conda.exports.handle_proxy_407` as pending deprecation. (#11597)
* Refactor `conda.activate._Activator.get_export_unset_vars` to use `**kwargs` instead of `OrderedDict`. (#11649)
* Mark `conda.another_to_unicode` as pending deprecation. (#11678)

### Docs

* Corresponding documentation of `notices` subcommand. (#11462)
* Corresponding documentation of `rename` subcommand. (#11496)
* Correct docs URL to https://docs.conda.io. (#11508)
* Updated the list of environment variables that can now expand in the [Use Condarc](https://docs.conda.io/projects/conda/en/latest/user-guide/configuration/use-condarc.html#expansion-of-environment-variables) section. (#11514)
* Include notice that the "All Users" installation option in the Anaconda Installer is no longer available due to [security concerns](https://github.com/ContinuumIO/anaconda-distribution-installer/commit/301e84f84b63d654045d4d7871b726de39fc9bb5). (#11528)
* Update [`conda-zsh-completeion` link](https://github.com/conda-incubator/conda-zsh-completion). (#11541)
* Missing `pip` as a dependency when including a pip-installed dependency. (#11543)
* Convert `README.rst` to `README.md`. (#11544)
* Updated docs and CLI help to include information on `conda init` arguments. (#11574)
* Added docs for writing integration tests. (#11604)
* Updated `conda env create` CLI documentation description and examples to be more helpful. (#11611)

### Other


* Display tests summary in CI. (#11558)
* Update `Dockerfile` and `ci-images.yml` flow to build multi arch images. (#11560)
* Rename master branch to main. (#11570)

### Contributors

* @drewja made their first contribution in #11614
* @beeankha
* @topherocity made their first contribution in #11658
* @conda-bot
* @dandv made their first contribution in #11636
* @dbast
* @dholth
* @deepyaman made their first contribution in #11598
* @dogukanteber made their first contribution in #11556/#11630
* @jaimergp
* @kathatherine
* @kenodegard
* @nps1ngh made their first contribution in #10764
* @pseudoyim made their first contribution in #11528
* @SamStudio8 made their first contribution in #11679
* @SamuelWN made their first contribution in #11543
* @spencermathews made their first contribution in #11508
* @timgates42
* @timhoffm made their first contribution in #11601
* @travishathaway
* @esc
* @pre-commit-ci[bot]



## 4.13.0 (2022-05-19)

### Enhancements

* Introducing `conda clean --logfiles` to remove logfiles generated by conda-libmamba-solver. (#11387)
* Add the solver name and version to the user-agent. (#11415, #11455)
* Attempt parsing HTTP errors as a JSON and extract error details. If present, prefer these details instead of those hard-coded. (#11440)

### Bug fixes

* Fix inconsistencies with `conda clean --dryrun` (#11385)
* Standardize tarball & package finding in `conda clean` (#11386, #11391)
* Fix `escape_channel_url` logic on Windows (#11416)
* Use 'Accept' header, not 'Content-Type' in GET header (#11446)
* Allow extended user-agent collection to fail but log the exception (#11455)

### Deprecations

* Removing deprecated `conda.cli.activate`. Originally deprecated in conda 4.6.0 in May 2018. (#11309)
* Removing deprecated `conda.compat`. Originally deprecated in conda 4.6.0 in May 2018. (#11322)
* Removing deprecated `conda.install`. Originally deprecated in conda 4.6.0 in May 2018. (#11323)
* Removing deprecated `conda.cli.main_help`. Originally deprecated in conda 4.6.0 in May 2018. (#11325)
* Removed unused `conda.auxlib.configuration`. (#11349)
* Removed unused `conda.auxlib.crypt`. (#11349)
* Removed unused `conda.auxlib.deprecation`. (#11349)
* Removed unused `conda.auxlib.factory`. (#11349)
* Removed minimally used `conda.auxlib.path`. (#11349)
* Removed `conda.exports.CrossPlatformStLink`, a Windows Python <3.2 fix for `os.lstat.st_nlink`. (#11351)
* Remove Python 2.7 and other legacy code (#11364)
* `conda run --live-stream` aliases `conda run --no-capture-output`. (#11422)
* Removes unused exceptions. (#11424)
* Combines conda_env.exceptions with conda.exceptions. (#11425)
* Drop Python 3.6 support. (#11453)
* Remove outdated test `test_init_dev_and_NoBaseEnvironmentError` (#11469)

### Docs

* Initial implementation of deep dive docs (#11059)
* Correction of RegisterPython description in Windows Installer arguments. (#11312)
* Added autodoc documentation for `conda compare`. (#11336)
* Remove duplicated instruction in manage-python.rst (#11381)
* Updated conda cheatsheet. (#11443)
* Fix typos throughout the codebase (#11448)
* Fix `conda activate` example (#11471)
* Updated `conda` 4.12 cheatsheet with new anaconda distribution version (#11479)

### Other

* Add Python 3.10 as a test target. (#10992)
* Replace custom `conda._vendor` with [vendoring](https://github.com/pradyunsg/vendoring) (#11290)
* Replace `conda.auxlib.collection.frozendict` with vendored `frozendict` (#11398)
* Reorganize and new tests for `conda.cli.main_clean` (#11360)
* Removing vendored usage of urllib3 and instead implementing our own wrapper around std. lib urllib (#11373)
* Bump vendored `py-cpuinfo` version 4.0.0 → 8.0.0. (#11393)
* Add informational Codecov status checks (#11400)

### Contributors

* @beeankha made their first contribution in #11469
* @ChrisPanopoulos made their first contribution in #11312
* @conda-bot
* @dholth
* @jaimergp
* @jezdez
* @kathatherine made their first contribution in #11443
* @kenodegard
* @kianmeng made their first contribution in #11448
* @simon9500 made their first contribution in #11381
* @thomasrockhu-codecov made their first contribution in #11400
* @travishathaway made their first contribution in #11373
* @pre-commit-ci[bot]



## 4.12.0 (2022-03-08)

### Enhancements

* Add support for libmamba integrations. (#11193)

  This is a new **experimental and opt-in** feature that allows use of the new
  [conda-libmamba-solver](https://github.com/conda-incubator/conda-libmamba-solver)
  for an improved user experience, based on the libmamba community project -
  the library version of the [mamba package manager](https://github.com/mamba-org/mamba).

  Please follow these steps to try out the new libmamba solver integration:

  1. Make sure you have [conda-libmamba-solver](https://github.com/conda-incubator/conda-libmamba-solver)
     installed in your conda base environment.

  2. Try out the solver using the `--experimental-solver=libmamba` command line option.

     E.g. with a dry-run to install the ``scipy`` package:

     ```
     conda create -n demo scipy --dry-run --experimental-solver=libmamba
     ```

     Or install in an activated conda environment:

     ```
     conda activate my-environment
     conda install scipy --experimental-solver=libmamba
     ```

* Make sure that `conda env update -f` sets env vars from the referenced yaml file. (#10652)
* Improve command line argument quoting, especially for `conda run`. (#11189)
* Allow `conda run` to work in read-only environments. (#11215)
* Add support for prelink_message. (#11123)
* Added `conda.CONDA_SOURCE_ROOT`. (#11182)

### Bug fixes

* Refactored `conda.utils.ensure_comspec_set` into `conda.utils.get_comspec`. (#11168)
* Refactored `conda.cli.common.is_valid_prefix` into `conda.cli.common.validate_prefix`. (#11172)
* Instantiate separate S3 session for thread-safety. (#11038)
* Change overly verbose info log to debug. (#11260)
* Remove five.py and update metaclass definitions. (#11267)
* Remove unnecessary conditional in setup.py (#11013)

### Docs

* Clarify on AIE messaging in download.rst. (#11221)
* Fix conda environment variable echo, update example versions. (#11237)
* Fixed link in docs. (#11268)
* Update profile examples. (#11278)
* Fix typos. (#11070)
* Document conda run command. (#11299)

### Other

* Added macOS to continuous integration. (#10875)
* Added ability to build per-pullrequest review builds. (#11135)
* Improved subprocess handling on Windows. (#11179)
* Add `CONDA_SOURCE_ROOT` env var. (#11182)
* Automatically check copyright/license disclaimer & encoding pragma. (#11183)
* Development environment per Python version. (#11233)
* Add concurrency group to cancel GHA runs on repeated pushes to branch/PR. (#11258)
* Only run GHAs on non-forks. (#11265)

### Contributors

* @opoplawski
* @FaustinCarter
* @jaimergp
* @rhoule-anaconda
* @jezdez
* @hajapy
* @erykoff
* @uwuvalon
* @kenodegard
* @manics
* @NaincyKumariKnoldus
* @autotmp
* @yuvipanda
* @astrojuanlu
* @marcelotrevisani

## 4.11.0 (2021-11-22)

### Enhancements

* Allow channel_alias to interpolate environment variables.
* Support running conda with PyPy on Windows.
* Add ability to add, append and prepend to sequence values when using the conda config subcommand.
* Support Python 3.10 in version parser.
* Add `XDG_CONFIG_HOME` to the conda search path following the [XDG Base Directory Specification (XDGBDS)](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html).

### Bug fixes

* Fix the PowerShell activator to not show an error when unsetting environment variables.
* Remove superfluous `eval` statements in fish shell integration.
* Indent the conda fish integration file using fish_indent.
* Fix handling of environment variables containing equal signs (`=`).
* Handle permission errors when listing all known prefixes.
* Catch Unicode decoding errors when parsing conda-meta files.
* Fix handling write errors when trying to create package cache or env directories.

### Docs

* Update path of conda repo in RHEL based systems to `/etc/yum.repos.d/conda.repo`.
* Fix the advanced pip example to stop using the now invalid `file:` prefix.
* Minor docs cleanup and adding Code of Conduct.
* Add auto-built architecture documentation for conda based on the [C4 Model](https://c4model.com). See the conda documentation for more information.
* Expand the contributing documentation with a section about static code analysis and code linting.
* Add [developer guide section](https://docs.conda.io/projects/conda/en/latest/dev-guide/) to the documentation, including a conda [architecture overview](https://docs.conda.io/projects/conda/en/latest/architecture.html).
* Stop referring to updating anaconda when `conda update` fails with an error.

### Other

* Build Docker images periodically on GitHub Actions for the continuous integration testing on Linux, storing them on GitHub Packages's registry for reduced latency and cost when using Docker Hub.

* Simplify the Linux GitHub actions workflows by combining used shell scripts.
* Add periodic GitHub Actions workflow to review old issues in the conda issue tracker and mark them as stale if no feedback is provided in a sensible amount of time, eventually closing them.
* Add periodic GitHub Actions workflow to lock the comment threads of old issues and pull requests in the conda GitHub repository to surface regressions with new issues instead.
* Refactor test suite to use more GitHub Actions runners in parallel, reducing total run time by 50%.
* Switched the issue tracker to use forms with additional questions for bug reporters to help in ticket triage.
* Add and automatically run pre-commit as part of the CI system to improve the code quality continuously and raise issues in contributed patches early on.

  The used code linters are: [flake8](https://flake8.pycqa.org/), [pylint](https://pylint.org/) and [bandit](https://bandit.readthedocs.io/).

  The [Python code formatter black](https://black.readthedocs.io/) is used as well but is only enforced on changed code in a commit and not to the whole code base at once.
* Automatically build the conda package upon the successful merge into the master branch and upload it to the conda-canary channel on anaconda.org.

  To try conda out simply run:

  ```
  conda install -c conda-canary/label/dev conda
  ```
* Automate adding new issues to [public GitHub project board](https://github.com/orgs/conda/projects/4) to facilitate issue triage.

* Update GitHub issue and pull request labels to be more consistent.
* Start using [rever](https://regro.github.io/rever-docs/) for release management.
* (preview) Enable one-click gitpod and GitHub Codespaces setup for Linux development.

### Contributors

* Benjamin Bertrand
* Chawye Hsu
* Cheng H. Lee
* Dan Meador
* Daniel Bast
* Daniel Holth
* Gregor Kržmanc
* Hsin-Hsiang Peng
* Ilan Cosman
* Isuru Fernando
* Jaime Rodríguez-Guerra
* Jan-Benedikt Jagusch
* Jannis Leidel
* John Flavin
* Jonas Haag
* Ken Odegard
* Kfir Zvi
* Mervin Fansler
* bfis
* mkincaid
* pre-commit CI

## 4.10.3 (2021-06-29)

### Bug fixes

* Reverts "Don't create an unused S3 client at import time (#10516)"
  in 4.10.2 that introduced a regression for users using S3 based
  channels. (#10756)

## 4.10.2 (2021-06-25)

### Enhancements

* Add `--dry-run` option to `conda env create` (#10635)
* Print warning about pip-installed dependencies only once (#10638)
* Explicit install now respects `--download-only` flag (#10688)
* Bump vendored tqdm version (#10721)

### Bug fixes

* Fix `changeps1` handling for PowerShell (#10624)
* Handle unbound `$PS1` so sh activation does not fail with `set -u` (#10701)
* Fix sh activation so `$PATH` is properly restored on errors (#10631)
* Fix `-c` option handling so defaults channel is not always re-added (#10735)
* Fix artifact verification-related warnings and errors (#10627, #10677)
* Fix log level used in `conda/core/prefix_data.py` (#9998)
* Fix log level used when fetching artifact verification metadata (#10621)
* Don't create an unused S3 client at import time (#10516)
* Don't load `binstar_client` until needed (#10692)
* Reflect dropping of older Python versions in `setup.py` (#10642)

### Docs

* Merge release notes and changelog to reduce maintenance burden (#10745)
* Add mentions to PyPy, Anaconda terms of service (#10329, #10712)
* Update Python versions in examples (#10329, #10744)
* Update install macOS instructions (#10728)

### Contributors

* @AlbertDeFusco
* @awwad
* @casperdcl
* @cgranade
* @chenghlee
* @ColemanTom
* @dan-hook
* @dbast
* @ericpre
* @HedgehogCode
* @jamesp
* @jezdez
* @johnhany97
* @lightmare
* @mattip
* @maxerbubba
* @mrakitin
* @stinos
* @thermokarst


## 4.10.1 (2021-04-12)

### Bug fixes

* Fix version detection for `__linux` virtual package (#10599)
* Fix import from `conda_content_trust` (#10589)
* Fix how URL for verification metadata files are constructed (#10617)
* Partially fix profile `$PATH` setup on MSYS2 (#10459)
* Remove `.empty` directory even when `rsync` is not installed (#10331)

### Contributors

* @awwad
* @chenghlee
* @codepage949
* @niklasholm


## 4.10.0 (2021-03-30)

**NOTE**: This release formally drops support for Python 2.7 and Python < 3.6.

### Enhancements

* Add pilot support for metadata signatures and verification (#10578)
* Add `__linux` virtual package (#10552, #10561)
* Support nested keys when using `conda config --get` (#10447, #10572)
* Support installing default packages when using `conda env create` (#10530)
* Support HTTP sources for `conda env update -f` (#10536)
* Make macOS code signing operations less verbose (#10372)

### Bug fixes

* Fix `conda search` crashing on Python 3.9 (#10542)
* Allow `{channel}::pip` to satisfy pip requirements (#10550)
* Support `{host}:{port}` specifications in environment YAML files (#10417)
* Fall back to system `.condarc` if user `.condarc` is absent (#10479)
* Try UTF-16 if UTF-8 fails when reading environment YAML files (#10356)
* Properly parse Python version >= 3.10 (#10478)
* Fix zsh initialization when `$ZDOTDIR` is defined (#10413)
* Fix path handling for csh (#10410)
* Fix `setup.py` requirement for vendored `ruamel_yaml_conda` (#10441)
* Fix errors when pickling vendored `auxlib` objects (#10386)

### Docs

* Document the `__unix` and `__windows` virtual packages (#10511)
* Update list of supported and default versions of Python (#10531)
* Favor using `pip` instead of `setup.py` when setting up CI (#10308)

### Miscellaneous

* CI: drop Python 2.7 and add Python 3.9 (#10548)

### Contributors

* @awwad
* @BastianZim
* @beenje
* @bgobbi
* @blubs
* @chenghlee
* @cjmartian
* @ericpre
* @erykoff
* @felker
* @giladmaya
* @jamesmyatt
* @mingwandroid
* @opoplawski
* @saadparwaiz1
* @saucoide


## 4.9.2 (2020-11-10)

### Enhancements

* Use vendored `tqdm` in `conda.resolve` for better consistency (#10337)

### Bug fixes

* Revert to previous naming scheme for repodata cache files when
  `use_only_tar_bz2` config option is false (#10350)

### Docs

* Fix missing release notes (#10342)
* Fix permission errors when configuring deb repositories (#10347)

### Contributors

* @chenghlee
* @csoja
* @dylanmorroll
* @sscherfke


## 4.9.1 (2020-10-26)

### Enhancements

* Respect PEP 440 `~=` "compatible release" clause (#10313)

### Bug fixes

* Remove `preload_openssl` for Win32 (#10298)
* Add `if exist` to Windows registry hook (#10305)

### Contributors

* @mingwandroid


## 4.9.0 (2020-10-19)

### Enhancements

* Add `osx-arm64` as a recognized platform (#10128, #10134, #10137)
* Resign files modified during installation on ARM64 macOS (#10260)
* Add `__archspec` virtual package to identify CPU microarchitecture (#9930)
* Add `__unix` and `__win` virtual packages (#10214)
* Add `--no-capture--output` option to `conda run` (#9646)
* Add `--live-stream` option to `conda run` (#10270)
* Export and import environment variables set using `conda env config` (#10169)
* Cache repodata from `file://` channels (#9730)
* Do not relink already-installed packages (#10208)
* Speed up JSON formatting in logz module (#10189)


### Bug fixes:

* Stop `env remove --dry-run` from actually removing environments (#10261)
* Virtual package requirements are now considered by the solver (#10057)
* Fix cached filename processing when using only tar.bz2 (#10193)
* Stop showing solver hints about CUDA when it is not a dependency (#10275)
* Ignore virtual packages when checking environment consistency (#10196)
* Fix `config --json` output errors in certain circumstances (#10194)
* More consistent error handling by `conda shell` (#10238)
* Bump vendored version of tqdm to fix various threading and I/O bugs (#10266)


### Docs

* Correctly state default `/AddToPath` option in Windows installer (#10179)
* Fix typos in `--repodata-fn` help text (#10279)


### Miscellaneous

* Update CI infrastructure to use GitHub Actions (#10176, #10186, #10234)
* Update README badge to show GitHub Actions status (#10254)


### Contributors

* @AlbertDeFusco
* @angloyna
* @bbodenmiller
* @casperdcl
* @chenghlee
* @chrisburr
* @cjmartian
* @dhirschfeld
* @ericpre
* @gabrielcnr
* @InfiniteChai
* @isuruf
* @jjhelmus
* @LorcanHamill
* @maresb
* @mingwandroid
* @mlline00
* @xhochy
* @ydmytryk


## 4.8.5 (2020-09-14)

### Enhancements

* Add `osx-arm64` as a recognized platform (#10128, #10134)

### Contributors

* @isuruf
* @jjhelmus


## 4.8.4 (2020-08-06)

### Enhancements

* Add `linux-ppc64` as a recognized platform (#9797, #9877)
* Add `linux-s390x` as a recognized platform (#9933, #10051)
* Add spinner to pip installer (#10032)
* Add support for running conda in PyPy (#9764)
* Support creating conda environments using remote specification files (#9835)
* Allow request retries on various HTTP errors (#9919)
* Add `compare` command for environments against a specification file (#10022)
* Add (preliminary) support for JSON-format activation (#8727)
* Properly handle the `CURL_CA_BUNDLE` environment variable (#10078)
* More uniformly handle `$CONDA_PREFIX` when exporting environments (#10092)
* Enable trailing `_` to anchor OpenSSL-like versions (#9859)
* Replace `listdir` and `glob` with `scandir` (#9889)
* Ignore virtual packages when searching for constrained packages (#10117)
* Add virtual packages to be considered in the solver (#10057)

### Bug fixes:

* Prevent `remove --all` from deleting non-environment directories (#10086)
* Prevent `create --dry-run --yes` from deleting existing environments (#10090)
* Remove extra newline from environment export file (#9649)
* Print help on incomplete `conda env config` command rather than crashing (#9660)
* Correctly set exit code/errorlevel when `conda run` exits (#9665)
* Send "inconsistent environment" warnings to stderr to avoid breaking JSON output (#9738)
* Fix output formatting from post-link scripts (#9841)
* Fix URL parsing for channel subdirs (#9844)
* Fix `conda env export -f` sometimes producing empty output files (#9909)
* Fix handling of Python releases with two-digit minor versions (#9999)
* Do not use gid to determine if user is an admin on \*nix platforms (#10002)
* Suppress spurious xonsh activation warnings (#10005)
* Fix crash when running `conda update --all` on a nonexistent environment (#10028)
* Fix collections import for Python 3.8 (#10093)
* Fix regex-related deprecation warnings (#10093, #10096)
* Fix logic error when running under Python 2.7 on 64-bit platforms (#10108)
* Fix Python 3.8 leaked semaphore issue (#10115)

### Docs

* Fix formatting and typos (#9623, #9689, #9898, #10042)
* Correct location for yum repository configuration files (#9988)
* Clarify usage for the `--channel` option (#10054)
* Clarify Python is not installed by default into new environments (#10089)

### Miscellaneous

* Fixes to tests and CI pipelines (#9842, #9863, #9938, #9960, #10010)
* Remove conda-forge dependencies for developing conda (#9857, #9871)
* Audit YAML usage for `safe_load` vs `round_trip_load` (#9902)

### Contributors

* @alanhdu
* @angloyna
* @Anthchirp
* @Arrowbox
* @bbodenmiller
* @beenje
* @bernardoduarte
* @birdsarah
* @bnemanich
* @chenghlee
* @ChihweiLHBird
* @cjmartian
* @ericpre
* @error404-beep
* @esc
* @hartb
* @hugobuddel
* @isuruf
* @jjhelmus
* @kalefranz
* @mingwandroid
* @mlline00
* @mparry
* @mrocklin
* @necaris
* @pdnm
* @pradghos
* @ravigumm
* @Reissner
* @scopatz
* @sidhant007
* @songmeixu
* @speleo3
* @tomsaleeba
* @WinstonPais


## 4.8.3 (2020-03-13)

### Docs

* Add release notes for 4.8.2 to docs (#9632)
* Fix typos in docs (#9637, #9643)
* Grammatical and formatting changes (#9647)

### Bug fixes:

* Account for channel is specs (#9748)

### Contributors

* @bernardoduarte
* @forrestwaters
* @jjhelmus
* @msarahan
* @rrigdon
* @timgates42


## 4.8.2 (2020-01-24)

### Enhancements

* Solver messaging improvements (#9560)

### Docs

* Added precedence and conflict info  (#9565)
* Added how to set env variables with config API  (#9536)
* Updated user guide, deleted Overview, minor clean up (#9581)
* Add code of conduct (#9601, #9602, #9603, #9603, #9604 #9605)

### Bug fixes:

* change fish prompt only if changeps1 is true  (#7000)
* make frozendict JSON serializable (#9539)
* Conda env create empty dir (#9543)


### Contributors

* @msarahan
* @jjhelmus
* @rrigdon
* @soapy1
* @teake
* @csoja
* @kfranz

## 4.8.1 (2019-12-19)

### Enhancements

* improve performance for conda run by avoiding Popen.communicate  (#9381)
* Put conda keyring in /usr/share/keyrings on Debian (#9424)
* refactor common.logic to fix some bugs and prepare for better modularity (#9427)
* Support nested configuration  (#9449)
* Support Object configuration parameters  (#9465)
* Use freeze_installed to speed up conda env update  (#9511)
* add networking args to conda env create (#9525)

### Docs

* fix string concatenation running words together regarding CONDA_EXE  (#9411)
* Fix typo ("list" -> "info")  (#9433)
* typo in condarc key envs_dirs  (#9478)
* Clarify channel priority and package sorting (#9492)
* improve description of DLL loading verification and activating environments  (#9453)
* Installing with specific build number  (#9534)

### Bug fixes:

* Fix calling python api run_command with list and string arguments  (#9331)
* revert init bash completion  (#9421)
* set tmp to shortened path that excludes spaces (#9409)
* avoid function redefinition upon resourcing conda.fish  (#9444)
* propagate pip error level when creating envs with conda env (#9460)
* fix incorrect chown call (#9464)
* Add subdir to PackageRecord dist_str  (#9418)
* Fix running conda activate in multiple processes on windows  (#9477)
* Don't check in pkgs for trash (#9472)
* remove setuptools from run_constrained in recipe  (#9485)
* Fix `__conda_activate` function to correctly return exit code  (#9532)
* fix overly greedy capture done by subprocess for conda run  (#9537)


### Contributors

* @AntoinePrv
* @brettcannon
* @bwildenhain
* @cjmartian
* @felker
* @forrestwaters
* @gilescope
* @isuruf
* @jeremyjliu
* @jjhelmus
* @jhultman
* @marcuscaisey
* @mbargull
* @mingwandroid
* @msarahan
* @okhoma
* @osamoylenko
* @rrigdon
* @rulerofthehuns
* @soapy1
* @tartansandal


## 4.8.0 (2019-11-04)

### Enhancements

* retry downloads if they fail, controlled by `remote_max_retries` and `remote_backoff_factor` configuration values (#9318)
* redact authentication information in some URLs (#9341)
* add osx version virtual package , `__osx` (#9349)
* add glibc virtual package, `__glibc` (#9358)

### Docs

* removeed references to MD5s from docs (#9247)
* Add docs on `CONDA_DLL_SEARCH_MODIFICATION_ENABLED` (#9286)
* document threads, spec history and configuration (#9327)
* more documentation on channels (#9335)
* document the .condarc search order (#9369)
* various minor documentation fixes (#9238, #9248, #9267, #9334, #9351, #9372, #9378, #9388, #9391, #9393)

### Bug fixes

* fix issues with xonsh activation on Windows (#8246)
* remove unsupported --lock argument from conda clean (#8310)
* do not add `sys_prefix_path` to failed activation or deactivation (#9282)
* fix csh setenv command (#9284)
* do not memorize `PackageRecord.combined_depends` (#9289)
* use `CONDA_INTERNAL_OLDPATH` rather than `OLDPATH` in activation script (#9303)
* fixes xonsh activation and tab completion (#9305)
* fix what channels are queried when context.offline is True (#9385)


### Contributors

* @analog-cbarber
* @andreasg123
* @beckermr
* @bryant1410
* @colinbrislawn
* @felker
* @forrestwaters
* @gabrielcnr
* @isuruf
* @jakirkham
* @jeremyjliu
* @jjhelmus
* @jooh
* @jpigla
* @marcelotrevisani
* @melund
* @mfansler
* @mingwandroid
* @msarahan
* @rrigdon
* @scopatz
* @soapy1
* @WillyChen123
* @xhochy


## 4.7.12 (2019-09-12)

### Enhancements

* add support for env file creation based on explicit specs in history (#9093)
* detect prefix paths when -p nor -n not given  (#9135)
* Add config parameter to disable conflict finding (for faster time to errors)  (#9190)

### Bug fixes

* fix race condition with creation of repodata cache dir  (#9073)
* fix ProxyError expected arguments  (#9123)
* makedirs to initialize .conda folder when registering env - fixes permission errors with .conda folders not existing when package cache gets created (#9215)
* fix list duplicates errors in reading repodata/prefix data  (#9132)
* fix neutered specs not being recorded in history, leading to unsatisfiable environments later  (#9147)
* Standardize "conda env list" behavior between platforms  (#9166)
* add JSON output to conda env create/update  (#9204)
* speed up finding conflicting specs (speed regression in 4.7.11)  (#9218)

### Contributors

* @beenje
* @Bezier89
* @cjmartian
* @forrestwaters
* @jjhelmus
* @martin-raden
* @msarahan
* @nganani
* @rrigdon
* @soapy1
* @WesRoach
* @zheaton


## 4.7.11 (2019-08-06)

### Enhancements

* add config for control of number of threads. These can be set in condarc or using environment variables. Names/default values are: `default_threads/None`, `repodata_threads/None`, `verify_threads/1`, `execute_threads/1` (#9044)

### Bug fixes

* fix repodata_fns from condarc not being respected (#8998)
* Fix handling of UpdateModifiers other than FREEZE_INSTALLED (#8999)
* Improve conflict finding graph traversal (#9006)
* Fix setuptools being removed due to conda run_constrains (#9014)
* Avoid calling find_conflicts until all retries are spent (#9015)
* refactor _conda_activate.bat in hopes of improving behavior in parallel environments (#9021)
* Add support for local version specs in PYPI installed packages (#9025)
* fix boto3 initialization race condition (#9037)
* Fix return condition in package_cache_data (#9039)
* utilize libarchive_enabled attribute provided by conda-package-handling to fall back to .tar.bz2 files only. (#9041, #9053)
* Fix menu creation on windows having race condition, leading to popups about python.exe not being found (#9044)
* Improve list error when egg-link leads to extra egg-infos (#9045)
* Fix incorrect RemoveError when operating on an env that has one of conda's deps, but is not the env in which the current conda in use resides (#9054)

### Docs

* Document new package format better
* Document `conda init` command
* Document availability of RSS feed for CDN-backed channels that clone

### Contributors

* @Bezier89
* @forrestwaters
* @hajapy
* @ihnorton
* @matthewwardrop
* @msarahan
* @rogererens
* @rrigdon
* @soapy1


## 4.7.10 (2019-07-19)

### Bug fixes

* fix merging of specs
* fix bugs in building of chains in prefix graph


### Contributors

* @msarahan


## 4.7.9 (2019-07-18)

### Bug fixes

* fix Non records in comprehension
* fix potential keyerror in depth-first search
* fix PackageNotFound attribute error

### Contributors

* @jjhelmus
* @msarahan


## 4.7.8 (2019-07-17)

### Improvements

* improve unsatisfiable messages - try to group and explain output better.  Remove lots of extraneous stuff that was showing up in 4.7.7 (#8910)
* preload openssl on windows to avoid library conflicts and missing library issues (#8949)

### Bug fixes

* fix handling of channels where more than one channel contains packages with similar name, subdir, version and build_number.  This was causing mysterious unsatisfiable errors for some users.  (#8938)
* reverse logic check in checking channel equality, because == is not reciprocal to != with py27 (no `__ne__`) (#8938)
* fix an infinite loop or otherwise large process with building the unsatisfiable info.  Improve the depth-first search implementation.  (#8941)
* streamline fallback paths to unfrozen solve in case frozen fails. (#8942)
* Environment activation output only shows `conda activate envname` now, instead of sometimes showing just `activate`.  (#8947)

### Contributors

* @forrestwaters
* @jjhelmus
* @katietz
* @msarahan
* @rrigdon
* @soapy1


## 4.7.7 (2019-07-12)

### Improvements

* When an update command doesn't do anything because installed software conflicts with the update, information about the conflict is shown, rather than just saying "all requests are already satisfied"  (#8899)

### Bug fixes

* fix missing package_type attr in finding virtual packages  (#8917)
* fix parallel operations of loading index to preserve channel ordering  (#8921, #8922)
* filter PrefixRecords out from PackageRecords when making a graph to show unsatisfiable deps.  Fixes comparison error between mismatched types.  (#8924)
* install entry points before running post-link scripts, because post link scripts may depend on entry points.  (#8925)

### Contributors

* @jjhelmus
* @msarahan
* @rrigdon
* @soapy1


## 4.7.6 (2019-07-11)

### Improvements

* Improve cuda virtual package conflict messages to show the `__cuda` virtual package as part of the conflict (#8834)
* add additional debugging info to Resolve.solve (#8895)

### Bug fixes

* deduplicate error messages being shown for post-link scripts.  Show captured stdout/stderr on failure  (#8833)
* fix the checkout step in the Windows dev env setup instructions (#8827)
* bail out early when implicit python pinning renders an explicit spec unsatisfiable (#8834)
* handle edge cases in pinned specs better (#8843)
* extract package again if url is None (#8868)
* update docs regarding indexing and subdirs (#8874)
* remove warning about conda-build needing an update that was bothering people (#8884)
* only add repodata fn into cache key when fn is not repodata.json (#8900)
* allow conda to be downgraded with an explicit spec (#8892)
* add target to specs from historic specs (#8901)
* improve message when solving with a repodata file before repodata.json fails (#8907)
* fix distutils usage for "which" functionality.  Fix inability to change python version in envs with noarch packages (#8909)
* fix anaconda metapackage being removed because history matching was too restrictive (#8911)
* make freezing less aggressive; add fallback to non-frozen solve (#8912)

### Contributors

* @forrestwaters
* @jjhelmus
* @mcopes73
* @msarahan
* @richardjgowers
* @rrigdon
* @soapy1
* @twinssbc

## 4.7.5 (2019-06-24)

### Improvements

* improve wording in informational message when a particular `*_repodata.json` can't be found.  No need for alarm.  (#8808)

### Bug fixes

* restore tests being run on win-32 appveyor  (#8801)
* fix Dist class handling of .conda files  (#8816)
* fix strict channel priority handling when a package is unsatisfiable and thus not present in the collection  (#8819)
* handle JSONDecodeError better when package is corrupted at extract time  (#8820)

### Contributors

* @dhirschfeld
* @msarahan
* @rrigdon


## 4.7.4 (2019-06-19)

### Improvements

* Revert to and improve the unsatisfiability determination from 4.7.2 that was reverted in 4.7.3.  It's faster.  (#8783)

### Bug fixes

* fix tcsh/csh init scripts  (#8792)

### Docs improvements

* clean up docs of run_command
* fix broken links
* update docs environment.yaml file to update conda-package-handling
* conda logo favicon
* update strict channel priority info
* noarch package content ported from conda-forge
* add info about conda-forge
* remove references to things as they were before conda 4.1.  That was a long time ago.  This is not a history book.

### Contributors

* @jjhelmus
* @msarahan
* @rrigdon
* @soapy1


## 4.7.3 (2019-06-14)

### Bug fixes

* target prefix overrid applies to entry points in addition to replacements in standard files  (#8769)
* Revert to solver-based unsatisfiability determination  (#8775)
* fix renaming of existing prompt function in powershell  (#8774)

### Contributors

* @jjhelmus
* @msarahan
* @rrigdon
* @ScottEvtuch


## 4.7.2 (2019-06-10)

### Behavior changes

* unsatisfiability is determined in a slightly different way now. It no longer
  uses the SAT solver, but rather determines whether any specs have no
  candidates at all after running through get_reduced_index. This has been
  faster in benchmarks, but we welcome further data from your use cases about
  whether this was a good change.  (#8741)
* when using the --only-deps flag for the `install` command, conda now
  explicitly records those specs in your history. This primarily serves to
  reduce conda accidentally removing packages that you have actually requested.  (#8766)

### Improvements

* UnsatisfiableError messages are now grouped into categories and explained a bit better.  (#8741)
* --repodata-fn argument can be passed multiple times to have more fallback
  paths. `repodata_fns` conda config setting does the same thing, but saves you
  from needing to do it for every command invocation.  (#8741)

### Bug fixes

* fix channel flip-flopping that was happening when adding a channel other than earlier ones  (#8741)
* refactor flow control for multiple repodata files to not use exceptions  (#8741)
* force conda to use only old .tar.bz2 files if conda-build <3.18.3 is
  installed. Conda-build breaks when inspecting file contents, and this is fixed
  in conda-build 3.18.3 (#8741)
* use --force when using rsync to improve behavior with folders that may exist
  in the destination somehow. (#8750)
* handle EPERM errors when renaming, because MacOS lets you remove or create
  files, but not rename them. Thanks Apple. (#8755)
* fix conda removing packages installed via `install` with --only-deps flag when
  either `update` or `remove` commands are run. See behavior changes above.
  (#8766)

### Contributors

* @csosborn
* @jjhelmus
* @katietz
* @msarahan
* @rrigdon


## 4.7.1 (2019-05-30)

### Improvements

* Base initial solver specs map on explicitly requested specs (new and historic)  (#8689)
* Improve anonymization of automatic error reporting  (#8715)
* Add option to keep using .tar.bz2 files, in case new .conda isn't working for whatever reason  (#8723)

### Bug fixes

* fix parsing hyphenated PyPI specs (change hyphens in versions to .)  (#8688)
* fix PrefixRecord creation when file inputs are .conda files  (#8689)
* fix PrefixRecord creation for pip-installed packages  (#8689)
* fix progress bar stopping at 75% (no extract progress with new libarchive)  (#8689)
* preserve pre-4.7 download() interface in conda.exports  (#8698)
* virtual packages (such as cuda) are represented by leading double underscores
  by convention, to avoid confusion with existing single underscore packages
  that serve other purposes (#8738)

### Deprecations/Breaking Changes

* The `--prune` flag no longer does anything. Pruning is implicitly the
  standard behavior now as a result of the initial solver specs coming from
  explicitly requested specs. Conda will remove packages that are not explicitly
  requested and are not required directly or indirectly by any explicitly
  installed package.

### Docs improvements

* Document removal of the `free` channel from defaults (#8682)
* Add reference to conda config --describe  (#8712)
* Add a tutorial for .condarc modification  (#8737)

### Contributors

* @alexhall
* @cjmartian
* @kalefranz
* @martinkou
* @msarahan
* @rrigdon
* @soapy1

## 4.7.0 (2019-05-17)

### Improvements

* Implement support for "virtual" CUDA packages, to make conda consider the system-installed CUDA driver and act accordingly  (#8267)
* Support and prefer new .conda file format where available  (#8265, #8639)
* Use comma-separated env names in prompt when stacking envs  (#8431)
* show valid choices in error messages for enums  (#8602)
* freeze already-installed packages when running `conda install` as a first attempt, to speed up the solve in existing envs.  Fall back to full solve as necessary  (#8260, #8626)
* add optimization criterion to prefer arch over noarch packages when otherwise equivalent  (#8267)
* Remove `free` channel from defaults collection.  Add `restore_free_channel` config parameter if you want to keep it.  (#8579)
* Improve unsatisfiable hints  (#8638)
* Add capability to use custom repodata filename, for smaller subsets of repodata  (#8670)
* Parallelize SubdirData readup  (#8670)
* Parallelize transaction verification and execution  (#8670)

### Bug fixes

* Fix PATH handling with deactivate.d scripts  (#8464)
* Fix usage of deprecated collections ABCs (#)
* fix tcsh/csh initialization block  (#8591)
* fix missing CWD display in powershell prompt  (#8596)
* `wrap_subprocess_call`: fallback to sh if no bash  (#8611)
* move `TemporaryDirectory` to avoid importing from `conda.compat`  (#8671)
* fix missing conda-package-handling dependency in dev/start  (#8624)
* fix `path_to_url` string index out of range error  (#8265)
* fix conda init for xonsh  (#8644)
* fix fish activation (#8645)
* improve error handling for read-only filesystems  (#8665, #8674)
* break out of minimization when bisection has nowhere to go  (#8672)
* Handle None values for link channel name gracefully  (#8680)

### Contributors

* @chrisburr
* @EternalPhane
* @jjhelmus
* @kalefranz
* @mbargull
* @msarahan
* @rrigdon
* @scopatz
* @seibert
* @soapy1
* @nehaljwani
* @nh3
* @teake
* @yuvalreches

## 4.6.14 (2019-04-17)

### Bug fixes

* export extra function in powershell Conda.psm1 script (fixes anaconda powershell prompt)  (#8570)

### Contributors

* @msarahan


## 4.6.13 (2019-04-16)

### Bug fixes

* disable ``test_legacy_repodata`` on win-32 (missing dependencies)  (#8540)
* Fix activation problems on windows with bash, powershell, and batch.  Improve tests. (#8550, #8564)
* pass -U flag to for pip dependencies in conda env when running "conda env update"  (#8542)
* rename ``conda.common.os`` to ``conda.common._os`` to avoid shadowing os built-in  (#8548)
* raise exception when pip subprocess fails with conda env  (#8562)
* fix installing recursive requirements.txt files in conda env specs with python 2.7  (#8562)
* Don't modify powershell prompt when "changeps1" setting in condarc is False  (#8465)

### Contributors

* @dennispg
* @jjhelmus
* @jpgill86
* @mingwandroid
* @msarahan
* @noahp


## 4.6.12 (2019-04-10)

### Bug fixes

* Fix compat import warning (#8507)
* Adjust collections import to avoid deprecation warning (#8499)
* Fix bug in CLI tests (#8468)
* Disallow the number sign in environment names (#8521)
* Workaround issues with noarch on certain repositories (#8523)
* Fix activation on Windows when spaces are in path (#8503)
* Fix conda init profile modification for powershell (#8531)
* Point conda.bat to condabin (#8517)
* Fix various bugs in activation (#8520, #8528)

### Docs improvements

* Fix links in README (#8482)
* Changelogs for 4.6.10 and 4.6.11 (#8502)

### Contributors

@Bezier89
@duncanmmacleod
@ivigamberdiev
@javabrett
@jjhelmus
@katietz
@mingwandroid
@msarahan
@nehaljwani
@rrigdon


## 4.6.11 (2019-04-04)

### Bug fixes

* Remove sys.prefix from front of PATH in basic_posix (#8491)
* add import to fix conda.core.index.get_index (#8495)

### Docs improvements

* Changelogs for 4.6.10

### Contributors

* @jjhelmus
* @mingwandroid
* @msarahan


## 4.6.10 (2019-04-01)

### Bug fixes

* Fix python-3 only FileNotFoundError usage in initialize.py  (#8470)
* Fix more JSON encode errors for the _Null data type (#8471)
* Fix non-posix-compliant == in conda.sh (#8475, #8476)
* improve detection of pip dependency in environment.yml files to avoid warning message (#8478)
* fix condabin\conda.bat use of dp0, making PATH additions incorrect (#8480)
* init_fish_user: don't assume config file exists  (#8481)
* Fix for chcp output ending with . (#8484)

### Docs improvements

* Changelogs for 4.6.8, 4.6.9

### Contributors

* @duncanmmacleod
* @nehaljwani
* @ilango100
* @jjhelmus
* @mingwandroid
* @msarahan
* @rrigdon


## 4.6.9 (2019-03-29)

### Improvements

* Improve CI for docs commits (#8387, #8401, #8417)
* Implement `conda init --reverse` to undo rc file and registry changes (#8400)
* Improve handling of unicode systems  (#8342, #8435)
* Force the "COMSPEC"  environment variable to always point to cmd.exe on windows.  This was an implicit assumption that was not always true.  (#8457, #8461)

### Bug fixes

* Add central C:/ProgramData/conda as a search path on Windows  (#8272)
* remove direct use of ruamel_yaml (prefer internal abstraction, yaml_load)  (#8392)
* Fix/improve `conda init` support for fish shell (#8437)
* Improve solver behavior in the presence of inconsistent environments (such as pip as a conda dependency of python, but also installed via pip itself) (#8444)
* Handle read-only filesystems for environments.txt (#8451, #8453)
* Fix conda env commands involving pip-installed dependencies being installed into incorrect locations  (#8435)

### Docs improvements

* updated cheatsheet  (#8402)
* updated color theme  (#8403)

### Contributors

* @blackgear
* @dhirschfeld
* @jakirkham
* @jjhelmus
* @katietz
* @mingwandroid
* @msarahan
* @nehaljwani
* @rrigdon
* @soapy1
* @spamlrot-tic

## 4.6.8 (2019-03-06)

### Bug fixes

* detect when parser fails to parse arguments  (#8328)
* separate post-link script running from package linking.  Do linking of all packages first, then run any post-link
  scripts after all packages are present.  Ideally, more forgiving in presence of cycles.  (#8350)
* quote path to temporary requirements files generated by conda env.  Fixes issues with spaces.  (#8352)
* improve some exception handling around checking for presence of folders in extraction of tarballs  (#8360)
* fix reporting of packages when channel name is None  (#8379)
* fix the post-creation helper message from "source activate" to "conda activate"  (#8370)
* Add safety checks for directory traversal exploits in tarfiles.  These may be disabled using the ``safety_checks``
  configuration parameter.  (#8374)

### Docs improvements

* document MKL DLL hell and new Python env vars to control DLL search behavior  (#8315)
* add github template for reporting speed issues  (#8344)
* add in better use of sphinx admonitions (notes, warnings) for better accentuation in docs  (#8348)
* improve skipping CI builds when only docs changes are involved  (#8336)

### Contributors

* @albertmichaelj
* @jjhelmus
* @matta9001
* @msarahan
* @rrigdon
* @soapy1
* @steffenvan


## 4.6.7 (2019-02-21)

### Bug fixes

* skip scanning folders for contents during reversal of transactions.  Just ignore folders.  A bit messier, but a lot faster.  (#8266)
* fix some logic in renaming trash files to fix permission errors  (#8300)
* wrap pip subprocess calls in conda-env more cleanly and uniformly  (#8307)
* revert conda prepending to PATH in cli main file on windows  (#8307)
* simplify ``conda run`` code to use activation subprocess wrapper.  Fix a few conda tests to use ``conda run``.  (#8307)

### Docs improvements

* fixed duplicated "to" in managing envs section (#8298)
* flesh out docs on activation  (#8314)
* correct git syntax for adding a remote in dev docs  (#8316)
* unpin sphinx version in docs requirements  (#8317)

### Contributors

* @jjhelmus
* @MarckK
* @msarahan
* @rrigdon
* @samgd


## 4.6.6 (2019-02-18)

### Bug fixes
* fix incorrect syntax prepending to PATH for conda CLI functionality  (#8295)
* fix rename_tmp.bat operating on folders, leading to hung interactive dialogs.  Operate only on files.  (#8295)

### Contributors
* @mingwandroid
* @msarahan


## 4.6.5 (2019-02-15)

### Bug fixes
* Make super in resolve.py python 2 friendly  (#8280)
* support unicode paths better in activation scripts on Windows (#)
* set PATH for conda.bat to include Conda's root prefix, so that libraries can be found when using conda when the root env is not activated  (#8287, #8292)
* clean up warnings/errors about rsync and trash files  (#8290)

### Contributors
* @jjhelmus
* @mingwandroid
* @msarahan
* @rrigdon


## 4.6.4 (2019-02-13)

### Improvements
* allow configuring location of instrumentation records  (#7849)
* prepend conda-env pip commands with env activation to fix library loading  (#8263)

### Bug fixes
* resolve #8176 SAT solver choice error handling  (#8248)
* document ``pip_interop_enabled`` config parameter  (#8250)
* ensure prefix temp files are inside prefix  (#8253)
* ensure ``script_caller`` is bound before use  (#8254)
* fix overzealous removal of folders after cleanup of failed post-link scripts  (#8259)
* fix #8264: Allow 'int' datatype for values to non-sequence parameters  (#8268)

### Deprecations/Breaking Changes
* remove experimental ``featureless_minimization_disabled`` feature flag  (#8249)

### Contributors
* @davemasino
* @geremih
* @jjhelmus
* @kalefranz
* @msarahan
* @minrk
* @nehaljwani
* @prusse-martin
* @rrigdon
* @soapy1


## 4.6.3 (2019-02-07)

### Improvements
* Implement ``-stack`` switch for powershell usage of conda (#8217)
* Enable system-wide initialization for conda shell support (#8219)
* Activate environments prior to running post-link scripts (#8229)
* Instrument more solve calls to prioritize future optimization efforts (#8231)
* print more env info when searching in envs (#8240)

### Bug fixes
* resolve #8178, fix conda pip interop assertion error with egg folders (#8184)
* resolve #8157, fix token leakage in errors and config output (#8163)
* resolve #8185, fix conda package filtering with embedded/vendored python metadata (#8198)
* resolve #8199, fix errors on .* in version specs that should have been specific to the ~= operator (#8208)
* fix .bat scripts for handling paths on Windows with spaces (#8215)
* fix powershell scripts for handling paths on Windows with spaces (#8222)
* handle missing rename script more gracefully (especially when updating/installing conda itself) (#8212)

### Contributors
* @dhirschfeld
* @jjhelmus
* @kalefranz
* @msarahan
* @murrayreadccdc
* @nehaljwani
* @rrigdon
* @soapy1


## 4.6.2 (2019-01-29)

### Improvements
* Documentation restructuring/improvements  (#8139, #8143)
* rewrite rm_rf to use native system utilities and rename trash files  (#8134)

### Bug fixes
* fix UnavailableInvalidChannel errors when only noarch subdir is present  (#8154)
* document, but disable the ``allow_conda_downgrades`` flag, pending re-examination of the warning, which was blocking conda operations after an upgrade-downgrade cycle across minor versions.  (#8160)
* fix conda env export missing pip entries without use of pip interop enabled setting  (#8165)

### Contributors
* @jjhelmus
* @msarahan
* @nehaljwani
* @rrigdon


## 4.5.13 (2019-01-29)

### Improvements
* document the allow_conda_downgrades configuration parameter (#8034)
* remove conda upgrade message (#8161)

### Contributors
* @msarahan
* @nehaljwani

## 4.6.1 (2019-01-21)

### Improvements
* optimizations in ``get_reduced_index`` (#8117, #8121, #8122)

### Bug Fixes
* fix faulty onerror call for rm (#8053)
* fix activate.bat to use more direct call to conda.bat (don't require conda init; fix non-interactive script) (#8113)

### Contributors
* @jjhelmus
* @msarahan
* @pv


## 4.6.0 (2019-01-15)

### New Feature Highlights
* resolve #7053 preview support for conda operability with pip; disabled by default (#7067, #7370, #7710, #8050)
* conda initialize (#6518, #7388, #7629)
* resolve #7194 add '--stack' flag to 'conda activate'; remove max_shlvl
  config (#7195, #7226, #7233)
* resolve #7087 add non-conda-installed python packages into PrefixData (#7067, #7370)
* resolve #2682 add 'conda run' preview support (#7320, #7625)
* resolve #626 conda wrapper for PowerShell (#7794, #7829)

### Deprecations/Breaking Changes
* resolve #6915 remove 'conda env attach' and 'conda env upload' (#6916)
* resolve #7061 remove pkgs/pro from defaults (#7162)
* resolve #7078 add deprecation warnings for 'conda.cli.activate',
  'conda.compat', and 'conda.install' (#7079)
* resolve #7194 add '--stack' flag to 'conda activate'; remove max_shlvl
  config (#7195)
* resolve #6979, #7086 remove Dist from majority of project (#7216, #7252)
* fix #7362 remove --license from conda info and related code paths (#7386)
* resolve #7309 deprecate 'conda info package_name' (#7310)
* remove 'conda clean --source-cache' and defer to conda-build (#7731)
* resolve #7724 move windows package cache and envs dirs back to .conda directory (#7725)
* disallow env names with colons (#7801)

### Improvements
* import speedups (#7122)
* --help cleanup (#7120)
* fish autocompletion for conda env (#7101)
* remove reference to 'system' channel (#7163)
* add http error body to debug information (#7160)
* warn creating env name with space is not supported (#7168)
* support complete MatchSpec syntax in environment.yml files (#7178)
* resolve #4274 add option to remove an existing environment with 'conda create' (#7133)
* add ability for conda prompt customization via 'env_prompt' config param (#7047)
* resolve #7063 add license and license_family to MatchSpec for 'conda search' (#7064)
* resolve #7189 progress bar formatting improvement (#7191)
* raise log level for errors to error (#7229)
* add to conda.exports (#7217)
* resolve #6845 add option -S / --satisfied-skip-solve to exit early for satisfied specs (#7291)
* add NoBaseEnvironmentError and DirectoryNotACondaEnvironmentError (#7378)
* replace menuinst subprocessing by ctypes win elevation (4.6.0a3) (#7426)
* bump minimum requests version to stable, unbundled release (#7528)
* resolve #7591 updates and improvements from namespace PR for 4.6 (#7599)
* resolve #7592 compatibility shims (#7606)
* user-agent context refactor (#7630)
* solver performance improvements with benchmarks in common.logic (#7676)
* enable fuzzy-not-equal version constraint for pip interop (#7711)
* add -d short option for --dry-run (#7719)
* add --force-pkgs-dirs option to conda clean (#7719)
* address #7709 ensure --update-deps unlocks specs from previous user requests (#7719)
* add package timestamp information to output of 'conda search --info' (#7722)
* resolve #7336 'conda search' tries "fuzzy match" before showing PackagesNotFound (#7722)
* resolve #7656 strict channel priority via 'channel_priority' config option or --strict-channel-priority CLI flag (#7729)
* performance improvement to cache __hash__ value on PackageRecord (#7715)
* resolve #7764 change name of 'condacmd' dir to 'condabin'; use on all platforms (#7773)
* resolve #7782 implement PEP-440 '~=' compatible release operator (#7783)
* disable timestamp prioritization when not needed (#7894, #8012)
* compile pyc files for noarch packages in batches (#8015)
* disable per-file sha256 safety checks by default; add extra_safety_checks condarc option to enable them (#8017)
* shorten retries for file removal on windows, where in-use files can't be removed (#8024)
* expand env vars in ``custom_channels``, ``custom_multichannels``, ``default_channels``, ``migrated_custom_channels``, and ``whitelist_channels`` (#7826)
* encode repodata to utf-8 while caching, to fix unicode characters in repodata (#7873)

### Bug Fixes
* fix #7107 verify hangs when a package is corrupted (#7131)
* fix #7145 progress bar uses stderr instead of stdout (#7146)
* fix typo in conda.fish (#7152)
* fix #2154 conda remove should complain if requested removals don't exist (#7135)
* fix #7094 exit early for --dry-run with explicit and clone (#7096)
* fix activation script sort order (#7176)
* fix #7109 incorrect chown with sudo (#7180)
* fix #7210 add suppressed --mkdir back to 'conda create' (fix for 4.6.0a1) (#7211)
* fix #5681 conda env create / update when --file does not exist (#7385)
* resolve #7375 enable conda config --set update_modifier (#7377)
* fix #5885 improve conda env error messages and add extra tests (#7395)
* msys2 path conversion (#7389)
* fix autocompletion in fish (#7575)
* fix #3982 following 4.4 activation refactor (#7607)
* fix #7242 configuration load error message (#7243)
* fix conda env compatibility with pip 18 (#7612)
* fix #7184 remove conflicting specs to find solution to user's active request (#7719)
* fix #7706 add condacmd dir to cmd.exe path on first activation (#7735)
* fix #7761 spec handling errors in 4.6.0b0 (#7780)
* fix #7770 'conda list regex' only applies regex to package name (#7784)
* fix #8076 load metadata from index to resolve inconsistent envs (#8083)

### Non-User-Facing Changes
* resolve #6595 use OO inheritance in activate.py (#7049)
* resolve #7220 pep8 project renamed to pycodestyle (#7221)
* proxy test routine (#7308)
* add .mailmap and .cla-signers (#7361)
* add copyright headers (#7367)
* rename common.platform to common.os and split among windows, linux, and unix utils (#7396)
* fix windows test failures when symlink not available (#7369)
* test building conda using conda-build (#7251)
* solver test metadata updates (#7664)
* explicitly add Mapping, Sequence to common.compat (#7677)
* add debug messages to communicate solver stages (#7803)
* add undocumented sat_solver config parameter (#7811)

### Preview Releases

* 4.6.0a1 at d5bec21d1f64c3bc66c2999cfc690681e9c46177 on 2018-04-20
* 4.6.0a2 at c467517ca652371ebc4224f0d49315b7ec225108 on 2018-05-01
* 4.6.0b0 at 21a24f02b2687d0895de04664a4ec23ccc75c33a on 2018-09-07
* 4.6.0b1 at 1471f043eed980d62f46944e223f0add6a9a790b on 2018-10-22
* 4.6.0rc1 at 64bde065f8343276f168d2034201115dff7c5753 on 2018-12-31

### Contributors
* @cgranade
* @fabioz
* @geremih
* @goanpeca
* @jesse-
* @jjhelmus
* @kalefranz
* @makbigc
* @mandeep
* @mbargull
* @msarahan
* @nehaljwani
* @ohadravid
* @teake


## 4.5.12 (2018-12-10)

### Improvements
* backport 'allow_conda_downgrade' configuration parameter, default is False (#7998)
* speed up verification by disabling per-file sha256 checks (#8017)
* indicate Python 3.7 support in setup.py file (#8018)
* speed up solver by reduce the size of reduced index (#8016)
* speed up solver by skipping timestamp minimization when not needed (#8012)
* compile pyc files more efficiently, will speed up install of noarch packages (#8025)
* avoid waiting for removal of files on Windows when possible (#8024)

### Bug Fixes
* update integration tests for removal of 'features' key (#7726)
* fix conda.bat return code (#7944)
* ensure channel name is not NoneType (#8021)

### Contributors
* @debionne
* @jjhelmus
* @kalefranz
* @msarahan
* @nehaljwani


## 4.5.11 (2018-08-21)

### Improvements
* resolve #7672 compatibility with ruamel.yaml 0.15.54 (#7675)

### Contributors
* @CJ-Wright
* @mbargull


## 4.5.10 (2018-08-13)

### Bug Fixes
* fix conda env compatibility with pip 18 (#7627)
* fix py37 compat 4.5.x (#7641)
* fix #7451 don't print name, version, and size if unknown (#7648)
* replace glob with fnmatch in PrefixData (#7645)

### Contributors
* @jesse-
* @nehaljwani


## 4.5.9 (2018-07-30)

### Improvements
* resolve #7522 prevent conda from scheduling downgrades (#7598)
* allow skipping feature maximization in resolver (#7601)

### Bug Fixes
* fix #7559 symlink stat in localfs adapter (#7561)
* fix #7486 activate with no PATH set (#7562)
* resolve #7522 prevent conda from scheduling downgrades (#7598)

### Contributors
* @kalefranz
* @loriab


## 4.5.8 (2018-07-10)

### Bug Fixes
* fix #7524 should_bypass_proxies for requests 2.13.0 and earlier (#7525)

### Contributors
* @kalefranz


## 4.5.7 (2018-07-09)

### Improvements
* resolve #7423 add upgrade error for unsupported repodata_version (#7415)
* raise CondaUpgradeError for conda version downgrades on environments (#7517)

### Bug Fixes
* fix #7505 temp directory for UnlinkLinkTransaction should be in target prefix (#7516)
* fix #7506 requests monkeypatch fallback for old requests versions (#7515)

### Contributors
* @kalefranz
* @nehaljwani


## 4.5.6 (2018-07-06)

### Bug Fixes
* resolve #7473 py37 support (#7499)
* fix #7494 History spec parsing edge cases (#7500)
* fix requests 2.19 incompatibility with NO_PROXY env var (#7498)
* resolve #7372 disable http error uploads and CI cleanup (#7498, #7501)

### Contributors
* @kalefranz


## 4.5.5 (2018-06-29)

### Bug Fixes
* fix #7165 conda version check should be restricted to channel conda is from (#7289, #7303)
* fix #7341 ValueError n cannot be negative (#7360)
* fix #6691 fix history file parsing containing comma-joined version specs (#7418)
* fix msys2 path conversion (#7471)

### Contributors
* @goanpeca
* @kalefranz
* @mingwandroid
* @mbargull


## 4.5.4 (2018-05-14)

### Improvements
* resolve #7189 progress bar improvement (#7191 via #7274)

### Bug Fixes
* fix twofold tarball extraction, improve progress update (#7275)
* fix #7253 always respect copy LinkType (#7269)

### Contributors
* @jakirkham
* @kalefranz
* @mbargull


## 4.5.3 (2018-05-07)

### Bug Fixes
* fix #7240 conda's configuration context is not initialized in conda.exports (#7244)


## 4.5.2 (2018-04-27)

### Bug Fixes
* fix #7107 verify hangs when a package is corrupted (#7223)
* fix #7094 exit early for --dry-run with explicit and clone (#7224)
* fix activation/deactivation script sort order (#7225)


## 4.5.1 (2018-04-13)

### Improvements
* resolve #7075 add anaconda.org search message to PackagesNotFoundError (#7076)
* add CondaError details to auto-upload reports (#7060)

### Bug Fixes
* fix #6703,#6981 index out of bound when running deactivate on fish shell (#6993)
* properly close over $_CONDA_EXE variable (#7004)
* fix condarc map parsing with comments (#7021)
* fix #6919 csh prompt (#7041)
* add _file_created attribute (#7054)
* fix handling of non-ascii characters in custom_multichannels (#7050)
* fix #6877 handle non-zero return in CSH (#7042)
* fix #7040 update tqdm to version 4.22.0 (#7157)


## 4.5.0 (2018-03-20)

### New Feature Highlights
* A new flag, '--envs', has been added to 'conda search'. In this mode,
  'conda search' will look for the package query in existing conda environments
  on your system. If ran as UID 0 (i.e. root) on unix systems or as an
  Administrator user on Windows, all known conda environments for all users
  on the system will be searched.  For example, 'conda search --envs openssl'
  will show the openssl version and environment location for all
  conda-installed openssl packages.

### Deprecations/Breaking Changes
* resolve #6886 transition defaults from repo.continuum.io to repo.anaconda.com (#6887)
* resolve #6192 deprecate 'conda help' in favor of --help CLI flag (#6918)
* resolve #6894 add http errors to auto-uploaded error reports (#6895)

### Improvements
* resolve #6791 conda search --envs (#6794)
* preserve exit status in fish shell (#6760)
* resolve #6810 add CONDA_EXE environment variable to activate (#6923)
* resolve #6695 outdated conda warning respects --quiet flag (#6935)
* add instructions to activate default environment (#6944)

### API
* resolve #5610 add PrefixData, SubdirData, and PackageCacheData to conda/api.py (#6922)

### Bug Fixes
* channel matchspec fixes (#6893)
* fix #6930 add missing return statement to S3Adapter (#6931)
* fix #5802, #6736 enforce disallowed_packages configuration parameter (#6932)
* fix #6860 infinite recursion in resolve.py for empty track_features (#6928)
* set encoding for PY2 stdout/stderr (#6951)
* fix #6821 non-deterministic behavior from MatchSpec merge clobbering (#6956)
* fix #6904 logic errors in prefix graph data structure (#6929)

### Non-User-Facing Changes
* fix several lgtm.com flags (#6757, #6883)
* cleanups and refactors for conda 4.5 (#6889)
* unify location of record types in conda/models/records.py (#6924)
* resolve #6952 memoize url search in package cache loading (#6957)


## 4.4.11 (2018-02-23)

### Improvements
* resolve #6582 swallow_broken_pipe context manager and Spinner refactor (#6616)
* resolve #6882 document max_shlvl (#6892)
* resolve #6733 make empty env vars sequence-safe for sequence parameters (#6741)
* resolve #6900 don't record conda skeleton environments in environments.txt (#6908)

### Bug Fixes
* fix potential error in ensure_pad(); add more tests (#6817)
* fix #6840 handle error return values in conda.sh (#6850)
* use conda.gateways.disk for misc.py imports (#6870)
* fix #6672 don't update conda during conda-env operations (#6773)
* fix #6811 don't attempt copy/remove fallback for rename failures (#6867)
* fix #6667 aliased posix commands (#6669)
* fix #6816 fish environment autocomplete (#6885)
* fix #6880 build_number comparison not functional in match_spec (#6881)
* fix #6910 sort key prioritizes build string over build number (#6911)
* fix #6914, #6691 conda can fail to update packages even though newer versions exist (#6921)
* fix #6899 handle Unicode output in activate commands (#6909)


## 4.4.10 (2018-02-09)

### Bug Fixes
* fix #6837 require at least futures 3.0.0 (#6855)
* fix #6852 ensure temporary path is writable (#6856)
* fix #6833 improve feature mismatch metric (via 4.3.34 #6853)


## 4.4.9 (2018-02-06)

### Improvements
* resolve #6632 display package removal plan when deleting an env (#6801)

### Bug Fixes
* fix #6531 don't drop credentials for conda-build workaround (#6798)
* fix external command execution issue (#6789)
* fix #5792 conda env export error common in path (#6795)
* fix #6390 add CorruptedEnvironmentError (#6778)
* fix #5884 allow --insecure CLI flag without contradicting meaning of ssl_verify (#6782)
* fix MatchSpec.match() accepting dict (#6808)
* fix broken Anaconda Prompt for users with spaces in paths (#6825)
* JSONDecodeError was added in Python 3.5 (#6848)
* fix #6796 update PATH/prompt on reactivate (#6828)
* fix #6401 non-ascii characters on windows using expanduser (#6847)
* fix #6824 import installers before invoking any (#6849)


## 4.4.8 (2018-01-25)

### Improvements
* allow falsey values for default_python to avoid pinning python (#6682)
* resolve #6700 add message for no space left on device (#6709)
* make variable 'sourced' local for posix shells (#6726)
* add column headers to conda list results (#5726)

### Bug Fixes
* fix #6713 allow parenthesis in prefix path for conda.bat (#6722)
* fix #6684 --force message (#6723)
* fix #6693 KeyError with '--update-deps' (#6694)
* fix aggressive_update_packages availability (#6727)
* fix #6745 don't truncate channel priority map in conda installer (#6746)
* add workaround for system Python usage by lsb_release (#6769)
* fix #6624 can't start new thread (#6653)
* fix #6628 'conda install --rev' in conda 4.4 (#6724)
* fix #6707 FileNotFoundError when extracting tarball (#6708)
* fix #6704 unexpected token in conda.bat (#6710)
* fix #6208 return for no pip in environment (#6784)
* fix #6457 env var cleanup (#6790)
* fix #6645 escape paths for argparse help (#6779)
* fix #6739 handle unicode in environment variables for py2 activate (#6777)
* fix #6618 RepresenterError with 'conda config --set' (#6619)
* fix #6699 suppress memory error upload reports (#6776)
* fix #6770 CRLF for cmd.exe (#6775)
* fix #6514 add message for case-insensitive filesystem errors (#6764)
* fix #6537 AttributeError value for url not set (#6754)
* fix #6748 only warn if unable to register environment due to EACCES (#6752)


## 4.4.7 (2018-01-08)

### Improvements
* resolve #6650 add upgrade message for unicode errors in python 2 (#6651)

### Bug Fixes
* fix #6643 difference between '==' and 'exact_match_' (#6647)
* fix #6620 KeyError(u'CONDA_PREFIX',) (#6652)
* fix #6661 remove env from environments.txt (#6662)
* fix #6629 'conda update --name' AssertionError (#6656)
* fix #6630 repodata AssertionError (#6657)
* fix #6626 add setuptools as constrained dependency (#6654)
* fix #6659 conda list explicit should be dependency sorted (#6671)
* fix #6665 KeyError for channel '<unknown>' (#6668, #6673)
* fix #6627 AttributeError on 'conda activate' (#6655)


## 4.4.6 (2017-12-31)

### Bug Fixes
* fix #6612 do not assume Anaconda Python on Windows nor Library\bin hack (#6615)
* recipe test improvements and associated bug fixes (#6614)


## 4.4.5 (2017-12-29)

### Bug Fixes
* fix #6577, #6580 single quote in PS1 (#6585)
* fix #6584 os.getcwd() FileNotFound (#6589)
* fix #6592 deactivate command order (#6602)
* fix #6579 python not recognized as command (#6588)
* fix #6572 cached repodata PermissionsError (#6573)
* change instances of 'root' to 'base' (#6598)
* fix #6607 use subprocess rather than execv for conda command extensions (#6609)
* fix #6581 git-bash activation (#6587)
* fix #6599 space in path to base prefix (#6608)


## 4.4.4 (2017-12-24)

### Improvements
* add SUDO_ env vars to info reports (#6563)
* add additional information to the #6546 exception (#6551)

### Bug Fixes
* fix #6548 'conda update' installs packages not in prefix #6550
* fix #6546 update after creating an empty env (#6568)
* fix #6557 conda list FileNotFoundError (#6558)
* fix #6554 package cache FileNotFoundError (#6555)
* fix #6529 yaml parse error (#6560)
* fix #6562 repodata_record.json permissions error stack trace (#6564)
* fix #6520 --use-local flag (#6526)

## 4.4.3 (2017-12-22)

### Improvements
* adjust error report message (#6534)

### Bug Fixes
* fix #6530 package cache JsonDecodeError / ValueError (#6533)
* fix #6538 BrokenPipeError (#6540)
* fix #6532 remove anaconda metapackage hack (#6539)
* fix #6536 'conda env export' for old versions of pip (#6535)
* fix #6541 py2 and unicode in environments.txt (#6542)

### Non-User-Facing Changes
* regression tests for #6512 (#6515)


## 4.4.2 (2017-12-22)

### Deprecations/Breaking Changes
* resolve #6523 don't prune with --update-all (#6524)

### Bug Fixes
* fix #6508 environments.txt permissions error stack trace (#6511)
* fix #6522 error message formatted incorrectly (#6525)
* fix #6516 hold channels over from get_index to install_actions (#6517)


## 4.4.1 (2017-12-21)

### Bug Fixes
* fix #6512 reactivate does not accept arguments (#6513)


## 4.4.0 (2017-12-20)

### Recommended change to enable conda in your shell

With the release of conda 4.4, we recommend a change to how the `conda` command is made available to your shell environment. All the old methods still work as before, but you'll need the new method to enable the new `conda activate` and `conda deactivate` commands.

For the "Anaconda Prompt" on Windows, there is no change.

For Bourne shell derivatives (bash, zsh, dash, etc.), you likely currently have a line similar to

    export PATH="/opt/conda/bin:$PATH"

in your `~/.bashrc` file (or `~/.bash_profile` file on macOS).  The effect of this line is that your base environment is put on PATH, but without actually *activating* that environment. (In 4.4 we've renamed the 'root' environment to the 'base' environment.) With conda 4.4, we recommend removing the line where the `PATH` environment variable is modified, and replacing it with

    . /opt/conda/etc/profile.d/conda.sh
    conda activate base

In the above, it's assumed that `/opt/conda` is the location where you installed miniconda or Anaconda.  It may also be something like `~/Anaconda3` or `~/miniconda2`.

For system-wide conda installs, to make the `conda` command available to all users, rather than manipulating individual `~/.bashrc` (or `~/.bash_profile`) files for each user, just execute once

    $ sudo ln -s /opt/conda/etc/profile.d/conda.sh /etc/profile.d/conda.sh

This will make the `conda` command itself available to all users, but conda's base (root) environment will *not* be activated by default.  Users will still need to run `conda activate base` to put the base environment on PATH and gain access to the executables in the base environment.

After updating to conda 4.4, we also recommend pinning conda to a specific channel.  For example, executing the command

    $ conda config --system --add pinned_packages conda-canary::conda

will make sure that whenever conda is installed or changed in an environment, the source of the package is always being pulled from the `conda-canary` channel.  This will be useful for people who use `conda-forge`, to prevent conda from flipping back and forth between 4.3 and 4.4.


### New Feature Highlights

* **conda activate**: The logic and mechanisms underlying environment activation have been reworked. With conda 4.4, `conda activate` and `conda deactivate` are now the preferred commands for activating and deactivating environments. You'll find they are much more snappy than the `source activate` and `source deactivate` commands from previous conda versions. The `conda activate` command also has advantages of (1) being universal across all OSes, shells, and platforms, and (2) not having path collisions with scripts from other packages like python virtualenv's activate script.


* **constrained, optional dependencies**: Conda now allows a package to constrain versions of other packages installed alongside it, even if those constrained packages are not themselves hard dependencies for that package. In other words, it lets a package specify that, if another package ends up being installed into an environment, it must at least conform to a certain version specification. In effect, constrained dependencies are a type of "reverse" dependency. It gives a tool to a parent package to exclude other packages from an environment that might otherwise want to depend on it.

  Constrained optional dependencies are supported starting with conda-build 3.0 (via [conda/conda-build#2001[(https://github.com/conda/conda-build/pull/2001)). A new `run_constrained` keyword, which takes a list of package specs similar to the `run` keyword, is recognized under the `requirements` section of `meta.yaml`. For backward compatibility with versions of conda older than 4.4, a requirement may be listed in both the `run` and the `run_constrained` section. In that case older versions of conda will see the package as a hard dependency, while conda 4.4 will understand that the package is meant to be optional.

  Optional, constrained dependencies end up in `repodata.json` under a `constrains` keyword, parallel to the `depends` keyword for a package's hard dependencies.


* **enhanced package query language**: Conda has a built-in query language for searching for and matching packages, what we often refer to as `MatchSpec`. The MatchSpec is what users input on the command line when they specify packages for `create`, `install`, `update`, and `remove` operations. With this release, MatchSpec (rather than a regex) becomes the default input for `conda search`. We have also substantially enhanced our MatchSpec query language.

  For example,

      conda install conda-forge::python

  is now a valid command, which specifies that regardless of the active list of channel priorities, the python package itself should come from the `conda-forge` channel. As before, the difference between `python=3.5` and `python==3.5` is that the first contains a "*fuzzy*" version while the second contains an *exact* version. The fuzzy spec will match all python packages with versions `>=3.5` and `<3.6`. The exact spec will match only python packages with version `3.5`, `3.5.0`, `3.5.0.0`, etc. The canonical string form for a MatchSpec is thus

      (channel::)name(version(build_string))

  which should feel natural to experienced conda users. Specifications however are often necessarily more complicated than this simple form can support, and for these situations we've extended the specification to include an optional square bracket `[]` component containing comma-separated key-value pairs to allow matching on most any field contained in a package's metadata. Take, for example,

      conda search 'conda-forge/linux-64::*[md5=e42a03f799131d5af4196ce31a1084a7]' --info

  which results in information for the single package

  ```
  cytoolz 0.8.2 py35_0
  --------------------
  file name   : cytoolz-0.8.2-py35_0.tar.bz2
  name        : cytoolz
  version     : 0.8.2
  build string: py35_0
  build number: 0
  size        : 1.1 MB
  arch        : x86_64
  platform    : Platform.linux
  license     : BSD 3-Clause
  subdir      : linux-64
  url         : https://conda.anaconda.org/conda-forge/linux-64/cytoolz-0.8.2-py35_0.tar.bz2
  md5         : e42a03f799131d5af4196ce31a1084a7
  dependencies:
    - python 3.5*
    - toolz >=0.8.0
  ```

  The square bracket notation can also be used for any field that we match on outside the package name, and will override information given in the "simple form" position. To give a contrived example, `python==3.5[version='>=2.7,<2.8']` will match `2.7.*` versions and not `3.5`.


* **environments track user-requested state**: Building on our enhanced MatchSpec query language, conda environments now also track and differentiate (a) packages added to an environment because of an explicit user request from (b) packages brought into an environment to satisfy dependencies. For example, executing

      conda install conda-forge::scikit-learn

  will confine all future changes to the scikit-learn package in the environment to the conda-forge channel, until the spec is changed again. A subsequent command `conda install scikit-learn=0.18` would drop the `conda-forge` channel restriction from the package. And in this case, scikit-learn is the only user-defined spec, so the solver chooses dependencies from all configured channels and all available versions.


* **errors posted to core maintainers**: In previous versions of conda, unexpected errors resulted in a request for users to consider posting the error as a new issue on conda's github issue tracker. In conda 4.4, we've implemented a system for users to opt-in to sending that same error report via an HTTP POST request directly to the core maintainers.

  When an unexpected error is encountered, users are prompted with the error report followed by a `[y/N]` input. Users can elect to send the report, with 'no' being the default response. Users can also permanently opt-in or opt-out, thereby skipping the prompt altogether, using the boolean `report_errors` configuration parameter.


* **various UI improvements**: To push through some of the big leaps with transactions in conda 4.3, we accepted some regressions on progress bars and other user interface features. All of those indicators of progress, and more, have been brought back and further improved.


* **aggressive updates**: Conda now supports an `aggressive_update_packages` configuration parameter that holds a sequence of MatchSpec strings, in addition to the `pinned_packages` configuration parameter. Currently, the default value contains the packages `ca-certificates`, `certifi`, and `openssl`. When manipulating configuration with the `conda config` command, use of the `--system` and `--env` flags will be especially helpful here. For example,

      conda config --add aggressive_update_packages defaults::pyopenssl --system

  would ensure that, system-wide, solves on all environments enforce using the latest version of `pyopenssl` from the `defaults` channel.

      conda config --add pinned_packages python=2.7 --env

  would lock all solves for the current active environment to python versions matching `2.7.*`.


* **other configuration improvements**: In addition to `conda config --describe`, which shows detailed descriptions and default values for all available configuration parameters, we have a new `conda config --write-default` command. This new command simply writes the contents of `conda config --describe` to a condarc file, which is a great starter template. Without additional arguments, the command will write to the `.condarc` file in the user's home directory. The command also works with the `--system`, `--env`, and `--file` flags to write the contents to alternate locations.

  Conda exposes a tremendous amount of flexibility via configuration. For more information, [The Conda Configuration Engine for Power Users](https://www.continuum.io/blog/developer-blog/conda-configuration-engine-power-users) blog post is a good resource.


### Deprecations/Breaking Changes
* the conda 'root' environment is now generally referred to as the 'base' environment
* Conda 4.4 now warns when available information about per-path sha256 sums and file sizes
  do not match the recorded information.  The warning is scheduled to be an error in conda 4.5.
  Behavior is configurable via the `safety_checks` configuration parameter.
* remove support for with_features_depends (#5191)
* resolve #5468 remove --alt-hint from CLI API (#5469)
* resolve #5834 change default value of 'allow_softlinks' from True to False (#5835)
* resolve #5842 add deprecation warnings for 'conda env upload' and 'conda env attach' (#5843)

### API
* Add Solver from conda.core.solver with three methods to conda.api (4.4.0rc1) (#5838)

### Improvements
* constrained, optional dependencies (#4982)
* conda shell function (#5044, #5141, #5162, #5169, #5182, #5210, #5482)
* resolve #5160 conda xontrib plugin (#5157)
* resolve #1543 add support and tests for --no-deps and --only-deps (#5265)
* resolve #988 allow channel name to be part of the package name spec (#5365, #5791)
* resolve #5530 add ability for users to choose to post unexpected errors to core maintainers (#5531, #5571, #5585)
* Solver, UI, History, and Other (#5546, #5583, #5740)
* improve 'conda search' to leverage new MatchSpec query language (#5597)
* filter out unwritable package caches from conda clean command (#4620)
* envs_manager, requested spec history, declarative solve, and private env tests (#4676, #5114, #5094, #5145, #5492)
* make python entry point format match pip entry points (#5010)
* resolve #5113 clean up CLI imports to improve process startup time (#4799)
* resolve #5121 add features/track_features support for MatchSpec (#5054)
* resolve #4671 hold verify backoff count in transaction context (#5122)
* resolve #5078 record package metadata after tarball extraction (#5148)
* resolve #3580 support stacking environments (#5159)
* resolve #3763, #4378 allow pip requirements.txt syntax in environment files (#3969)
* resolve #5147 add 'config files' to conda info (#5269)
* use --format=json to parse list of pip packages (#5205)
* resolve #1427 remove startswith '.' environment name constraint (#5284)
* link packages from extracted tarballs when tarball is gone (#5289)
* resolve #2511 accept config information from stdin (#5309)
* resolve #4302 add ability to set map parameters with conda config (#5310)
* resolve #5256 enable conda config --get for all primitive parameters (#5312)
* resolve #1992 add short flag -C for --use-index-cache (#5314)
* resolve #2173 add --quiet option to conda clean (#5313)
* resolve #5358 conda should exec to subcommands, not subprocess (#5359)
* resolve #5411 add 'conda config --write-default' (#5412)
* resolve #5081 make pinned packages optional dependencies (#5414)
* resolve #5430 eliminate current deprecation warnings (#5422)
* resolve #5470 make stdout/stderr capture in python_api customizable (#5471)
* logging simplifications/improvements (#5547, #5578)
* update license information (#5568)
* enable threadpool use for repodata collection by default (#5546, #5587)
* conda info now raises PackagesNotFoundError (#5655)
* index building optimizations (#5776)
* fix #5811 change safety_checks default to 'warn' for conda 4.4 (4.4.0rc1) (#5824)
* add constrained dependencies to conda's own recipe (4.4.0rc1) (#5823)
* clean up parser imports (4.4.0rc2) (#5844)
* resolve #5983 add --download-only flag to create, install, and update (4.4.0rc2) (#5988)
* add ca-certificates and certifi to aggressive_update_packages default (4.4.0rc2) (#5994)
* use environments.txt to list all known environments (4.4.0rc2) (#6313)
* resolve #5417 ensure unlink order is correctly sorted (4.4.0) (#6364)
* resolve #5370 index is only prefix and cache in --offline mode (4.4.0) (#6371)
* reduce redundant sys call during file copying (4.4.0rc3) (#6421)
* enable aggressive_update_packages (4.4.0rc3) (#6392)
* default conda.sh to dash if otherwise can't detect (4.4.0rc3) (#6414)
* canonicalize package names when comparing with pip (4.4.0rc3) (#6438)
* add target prefix override configuration parameter (4.4.0rc3) (#6413)
* resolve #6194 warn when conda is outdated (4.4.0rc3) (#6370)
* add information to displayed error report (4.4.0rc3) (#6437)
* csh wrapper (4.4.0) (#6463)
* resolve #5158 --override-channels (4.4.0) (#6467)
* fish update for conda 4.4 (4.4.0) (#6475, #6502)
* skip an unnecessary environments.txt rewrite (4.4.0) (#6495)

### Bug Fixes
* fix some conda-build compatibility issues (#5089)
* resolve #5123 export toposort (#5124)
* fix #5132 signal handler can only be used in main thread (#5133)
* fix orphaned --clobber parser arg (#5188)
* fix #3814 don't remove directory that's not a conda environment (#5204)
* fix #4468 _license stack trace (#5206)
* fix #4987 conda update --all no longer displays full list of packages (#5228)
* fix #3489 don't error on remove --all if environment doesn't exist (#5231)
* fix #1509 bash doesn't need full path for pre/post link/unlink scripts on unix (#5252)
* fix #462 add regression test (#5286)
* fix #5288 confirmation prompt doesn't accept no (#5291)
* fix #1713 'conda package -w' is case dependent on Windows (#5308)
* fix #5371 try falling back to pip's vendored requests if no requests available (#5372)
* fix #5356 skip root logger configuration (#5380)
* fix #5466 scrambled URL of non-alias channel with token (#5467)
* fix #5444 environment.yml file not found (#5475)
* fix #3200 use proper unbound checks in bash code and test (#5476)
* invalidate PrefixData cache on rm_rf for conda-build (#5491, #5499)
* fix exception when generating JSON output (#5628)
* fix target prefix determination (#5642)
* use proxy to avoid segfaults (#5716)
* fix #5790 incorrect activation message (4.4.0rc1) (#5820)
* fix #5808 assertion error when loading package cache (4.4.0rc1) (#5815)
* fix #5809 _pip_install_via_requirements got an unexpected keyword argument 'prune' (4.4.0rc1) (#5814)
* fix #5811 change safety_checks default to 'warn' for conda 4.4 (4.4.0rc1) (#5824)
* fix #5825 --json output format (4.4.0rc1) (#5831)
* fix force_reinstall for case when packages aren't actually installed (4.4.0rc1) (#5836)
* fix #5680 empty pip subsection error in environment.yml (4.4.0rc2) (#6275)
* fix #5852 bad tokens from history crash conda installs (4.4.0rc2) (#6076)
* fix #5827 no error message on invalid command (4.4.0rc2) (#6352)
* fix exception handler for 'conda activate' (4.4.0rc2) (#6365)
* fix #6173 double prompt immediately after conda 4.4 upgrade (4.4.0rc2) (#6351)
* fix #6181 keep existing pythons pinned to minor version (4.4.0rc2) (#6363)
* fix #6201 incorrect subdir shown for conda search when package not found (4.4.0rc2) (#6367)
* fix #6045 help message and zsh shift (4.4.0rc3) (#6368)
* fix noarch python package resintall (4.4.0rc3) (#6394)
* fix #6366 shell activation message (4.4.0rc3) (#6369)
* fix #6429 AttributeError on 'conda remove' (4.4.0rc3) (#6434)
* fix #6449 problems with 'conda info --envs' (#6451)
* add debug exception for #6430 (4.4.0rc3) (#6435)
* fix #6441 NotImplementedError on 'conda list' (4.4.0rc3) (#6442)
* fix #6445 scale back directory activation in PWD (4.4.0rc3) (#6447)
* fix #6283 no-deps for conda update case (4.4.0rc3) (#6448)
* fix #6419 set PS1 in python code (4.4.0rc3) (#6446)
* fix #6466 sp_dir doesn't exist (#6470)
* fix #6350 --update-all removes too many packages (4.4.0) (#6491)
* fix #6057 unlink-link order for python noarch packages on windows 4.4.x (4.4.0) (#6494)

### Non-User-Facing Changes
* eliminate index modification in Resolve init (#4333)
* new MatchSpec implementation (#4158, #5517)
* update conda.recipe for 4.4 (#5086)
* resolve #5118 organization and cleanup for 4.4 release (#5115)
* remove unused disk space check instructions (#5167)
* localfs adapter tests (#5181)
* extra config command tests (#5185)
* add coverage for confirm (#5203)
* clean up FileNotFoundError and DirectoryNotFoundError (#5237)
* add assertion that a path only has a single hard link before rewriting prefixes (#5305)
* remove pycrypto as requirement on windows (#5326)
* import cleanup, dead code removal, coverage improvements, and other
  housekeeping (#5472, #5474, #5480)
* rename CondaFileNotFoundError to PathNotFoundError (#5521)
* work toward repodata API (#5267)
* rename PackageNotFoundError to PackagesNotFoundError and fix message formatting (#5602)
* update conda 4.4 bld.bat windows recipe (#5573)
* remove last remnant of CondaEnvRuntimeError (#5643)
* fix typo (4.4.0rc2) (#6043)
* replace Travis-CI with CircleCI (4.4.0rc2) (#6345)
* key-value features (#5645); reverted in 4.4.0rc2 (#6347, #6492)
* resolve #6431 always add env_vars to info_dict (4.4.0rc3) (#6436)
* move shell inside conda directory (4.4.0) (#6479)
* remove dead code (4.4.0) (#6489)


## 4.3.34 (2018-02-09)

### Bug Fixes
* fix #6833 improve feature mismatch metric (#6853)


## 4.3.33 (2018-01-24)

### Bug Fixes
* fix #6718 broken 'conda install --rev' (#6719)
* fix #6765 adjust the feature score assigned to packages not installed (#6766)


## 4.3.32 (2018-01-10)

### Improvements
* resolve #6711 fall back to copy/unlink for EINVAL, EXDEV rename failures (#6712)

### Bug Fixes
* fix #6057 unlink-link order for python noarch packages on windows (#6277)
* fix #6509 custom_channels incorrect in 'conda config --show' (#6510)


## 4.3.31 (2017-12-15)

### Improvements
* add delete_trash to conda_env create (#6299)

### Bug Fixes
* fix #6023 assertion error for temp file (#6154)
* fix #6220 --no-builds flag for 'conda env export' (#6221)
* fix #6271 timestamp prioritization results in undesirable race-condition (#6279)

### Non-User-Facing Changes
* fix two failing integration tests after anaconda.org API change (#6182)
* resolve #6243 mark root as not writable when sys.prefix is not a conda environment (#6274)
* add timing instrumentation (#6458)


## 4.3.30 (2017-10-17)

### Improvements
* address #6056 add additional proxy variables to 'conda info --all' (#6083)

### Bug Fixes
* address #6164 move add_defaults_to_specs after augment_specs (#6172)
* fix #6057 add additional detail for message 'cannot link source that does not exist' (#6082)
* fix #6084 setting default_channels from CLI raises NotImplementedError (#6085)


## 4.3.29 (2017-10-09)

### Bug Fixes
* fix #6096 coerce to millisecond timestamps (#6131)


## 4.3.28 (2017-10-06)

### Bug Fixes
* fix #5854 remove imports of pkg_resources (#5991)
* fix millisecond timestamps (#6001)


## 4.3.27 (2017-09-18)

### Bug Fixes
* fix #5980 always delete_prefix_from_linked_data in rm_rf (#5982)


## 4.3.26 (2017-09-15)

### Deprecations/Breaking Changes
* resolve #5922 prioritize channels within multi-channels (#5923)
* add https://repo.continuum.io/pkgs/main to defaults multi-channel (#5931)

### Improvements
* add a channel priority minimization pass to solver logic (#5859)
* invoke cmd.exe with /D for pre/post link/unlink scripts (#5926)
* add boto3 use to s3 adapter (#5949)

### Bug Fixes
* always remove linked prefix entry with rm_rf (#5846)
* resolve #5920 bump repodata pickle version (#5921)
* fix msys2 activate and deactivate (#5950)


## 4.3.25 (2017-08-16)

### Deprecations/Breaking Changes
* resolve #5834 change default value of 'allow_softlinks' from True to False (#5839)

### Improvements
* add non-admin check to optionally disable non-privileged operation (#5724)
* add extra warning message to always_softlink configuration option (#5826)

### Bug Fixes
* fix #5763 channel url string splitting error (#5764)
* fix regex for repodata _mod and _etag (#5795)
* fix uncaught OSError for missing device (#5830)


## 4.3.24 (2017-07-31)

### Bug Fixes
* fix #5708 package priority sort order (#5733)


## 4.3.23 (2017-07-21)

### Improvements
* resolve #5391 PackageNotFound and NoPackagesFoundError clean up (#5506)

### Bug Fixes
* fix #5525 too many Nones in CondaHttpError (#5526)
* fix #5508 assertion failure after test file not cleaned up (#5533)
* fix #5523 catch OSError when home directory doesn't exist (#5549)
* fix #5574 traceback formatting (#5580)
* fix #5554 logger configuration levels (#5555)
* fix #5649 create_default_packages configuration (#5703)


## 4.3.22 (2017-06-12)

### Improvements
* resolve #5428 clean up cli import in conda 4.3.x (#5429)
* resolve #5302 add warning when creating environment with space in path (#5477)
* for ftp connections, ignore host IP from PASV as it is often wrong (#5489)
* expose common race condition exceptions in exports for conda-build (#5498)

### Bug Fixes
* fix #5451 conda clean --json bug (#5452)
* fix #5400 confusing deactivate message (#5473)
* fix #5459 custom subdir channel parsing (#5478)
* fix #5483 problem with setuptools / pkg_resources import (#5496)


## 4.3.21 (2017-05-25)

### Bug Fixes
* fix #5420 conda-env update error (#5421)
* fix #5425 is admin on win int not callable (#5426)


## 4.3.20 (2017-05-23)

### Improvements
* resolve #5217 skip user confirm in python_api, force always_yes (#5404)

### Bug Fixes
* fix #5367 conda info always shows 'unknown' for admin indicator on Windows (#5368)
* fix #5248 drop plan description information that might not always be accurate (#5373)
* fix #5378 duplicate log messages (#5379)
* fix #5298 record has 'build', not 'build_string' (#5382)
* fix #5384 silence logging info to avoid interfering with JSON output (#5393)
* fix #5356 skip root/conda logger init for cli.python_api (#5405)

### Non-User-Facing Changes
* avoid persistent state after channel priority test (#5392)
* resolve #5402 add regression test for #5384 (#5403)
* clean up inner function definition inside for loop (#5406)


## 4.3.19 (2017-05-18)

### Improvements
* resolve #3689 better error messaging for missing anaconda-client (#5276)
* resolve #4795 conda env export lacks -p flag (#5275)
* resolve #5315 add alias verify_ssl for ssl_verify (#5316)
* resolve #3399 add netrc existence/location to 'conda info' (#5333)
* resolve #3810 add --prefix to conda env update (#5335)

### Bug Fixes
* fix #5272 conda env export ugliness under python2 (#5273)
* fix #4596 warning message from pip on conda env export (#5274)
* fix #4986 --yes not functioning for conda clean (#5311)
* fix #5329 unicode errors on Windows (#5328, #5357)
* fix sys_prefix_unfollowed for Python 3 (#5334)
* fix #5341 --json flag with conda-env (#5342)
* fix 5321 ensure variable PROMPT is set in activate.bat (#5351)

### Non-User-Facing Changes
* test conda 4.3 with requests 2.14.2 (#5281)
* remove pycrypto as requirement on windows (#5325)
* fix typo avaialble -> available (#5345)
* fix test failures related to menuinst update (#5344, #5362)


## 4.3.18 (2017-05-09)

### Improvements
* resolve #4224 warn when pysocks isn't installed (#5226)
* resolve #5229 add --insecure flag to skip ssl verification (#5230)
* resolve #4151 add admin indicator to conda info on windows (#5241)

### Bug Fixes
* fix #5152 conda info spacing (#5166)
* fix --use-index-cache actually hitting the index cache (#5134)
* backport LinkPathAction verify from 4.4 (#5171)
* fix #5184 stack trace on invalid map configuration parameter (#5186)
* fix #5189 stack trace on invalid sequence config param (#5192)
* add support for the linux-aarch64 platform (#5190)
* fix repodata fetch with the `--offline` flag (#5146)
* fix #1773 conda remove spell checking (#5176)
* fix #3470 reduce excessive error messages (#5195)
* fix #1597 make extra sure --dry-run doesn't take any actions (#5201)
* fix #3470 extra newlines around exceptions (#5200)
* fix #5214 install messages for 'nothing_to_do' case (#5216)
* fix #598 stack trace for condarc write permission denied (#5232)
* fix #4960 extra information when exception can't be displayed (#5236)
* fix #4974 no matching dist in linked data for prefix (#5239)
* fix #5258 give correct element types for conda config --describe (#5259)
* fix #4911 separate shutil.copy2 into copy and copystat (#5261)

### Non-User-Facing Changes
* resolve #5138 add test of rm_rf of symlinked files (#4373)
* resolve #4516 add extra trace-level logging (#5249, #5250)
* add tests for --update-deps flag (#5264)


## 4.3.17 (2017-04-24)

### Improvements
* fall back to copy if hardlink fails (#5002)
* add timestamp metadata for tiebreaking conda-build 3 hashed packages (#5018)
* resolve #5034 add subdirs configuration parameter (#5030)
* resolve #5081 make pinned packages optional/constrained dependencies (#5088)
* resolve #5108 improve behavior and add tests for spaces in paths (#4786)

### Bug Fixes
* quote prefix paths for locations with spaces (#5009)
* remove binstar logger configuration overrides (#4989)
* fix #4969 error in DirectoryNotFoundError (#4990)
* fix #4998 pinned string format (#5011)
* fix #5039 collecting main_info shouldn't fail on requests import (#5090)
* fix #5055 improve bad token message for anaconda.org (#5091)
* fix #5033 only re-register valid signal handlers (#5092)
* fix #5028 imports in main_list (#5093)
* fix #5073 allow client_ssl_cert{_key} to be of type None (#5096)
* fix #4671 backoff for package validate race condition (#5098)
* fix #5022 gnu_get_libc_version => linux_get_libc_version (#5099)
* fix #4849 package name match bug (#5103)
* fixes #5102 allow proxy_servers to be of type None (#5107)
* fix #5111 incorrect typify for str + NoneType (#5112)

### Non-User-Facing Changes
* resolve #5012 remove CondaRuntimeError and RuntimeError (#4818)
* full audit ensuring relative import paths within project (#5090)
* resolve #5116 refactor conda/cli/activate.py to help menuinst (#4406)


## 4.3.16 (2017-03-30)

### Improvements
* additions to configuration SEARCH_PATH to improve consistency (#4966)
* add 'conda config --describe' and extra config documentation (#4913)
* enable packaging pinning in condarc using pinned_packages config parameter
  as beta feature (#4921, #4964)

### Bug Fixes
* fix #4914 handle directory creation on top of file paths (#4922)
* fix #3982 issue with CONDA_ENV and using powerline (#4925)
* fix #2611 update instructions on how to source conda.fish (#4924)
* fix #4860 missing information on package not found error (#4935)
* fix #4944 command not found error error (#4963)


## 4.3.15 (2017-03-20)

### Improvements
* allow pkgs_dirs to be configured using `conda config` (#4895)

### Bug Fixes
* remove incorrect elision of delete_prefix_from_linked_data() (#4814)
* fix envs_dirs order for read-only root prefix (#4821)
* fix break-point in conda clean (#4801)
* fix long shebangs when creating entry points (#4828)
* fix spelling and typos (#4868, #4869)
* fix #4840 TypeError reduce() of empty sequence with no initial value (#4843)
* fix zos subdir (#4875)
* fix exceptions triggered during activate (#4873)


## 4.3.14 (2017-03-03)

### Improvements
* use cPickle in place of pickle for repodata (#4717)
* ignore pyc compile failure (#4719)
* use conda.exe for windows entry point executable (#4716, #4720)
* localize use of conda_signal_handler (#4730)
* add skip_safety_checks configuration parameter (#4767)
* never symlink executables using ORIGIN (#4625)
* set activate.bat codepage to CP_ACP (#4558)

### Bug Fixes
* fix #4777 package cache initialization speed (#4778)
* fix #4703 menuinst PathNotFoundException (#4709)
* ignore permissions error if user_site can't be read (#4710)
* fix #4694 don't import requests directly in models (#4711)
* fix #4715 include resources directory in recipe (#4716)
* fix CondaHttpError for URLs that contain '%' (#4769)
* bug fixes for preferred envs (#4678)
* fix #4745 check for info/index.json with package is_extracted (#4776)
* make sure url gets included in CondaHTTPError (#4779)
* fix #4757 map-type configs set to None (#4774)
* fix #4788 partial package extraction (#4789)

### Non-User-Facing Changes
* test coverage improvement (#4607)
* CI configuration improvements (#4713, #4773, #4775)
* allow sha256 to be None (#4759)
* add cache_fn_url to exports (#4729)
* add unicode paths for PY3 integration tests (#4760)
* additional unit tests (#4728, #4783)
* fix conda-build compatibility and tests (#4785)


## 4.3.13 (2017-02-17)

### Improvements
* resolve #4636 environment variable expansion for pkgs_dirs (#4637)
* link, symlink, islink, and readlink for Windows (#4652, #4661)
* add extra information to CondaHTTPError (#4638, #4672)

### Bug Fixes
* maximize requested builds after feature determination (#4647)
* fix #4649 incorrect assert statement concerning package cache directory (#4651)
* multi-user mode bug fixes (#4663)

### Non-User-Facing Changes
* path_actions unit tests (#4654)
* remove dead code (#4369, #4655, #4660)
* separate repodata logic from index into a new core/repodata.py module (#4669)


## 4.3.12 (2017-02-14)

### Improvements
* prepare conda for uploading to pypi (#4619)
* better general http error message (#4627)
* disable old python noarch warning (#4576)

### Bug Fixes
* fix UnicodeDecodeError for ensure_text_type (#4585)
* fix determination of if file path is writable (#4604)
* fix #4592 BufferError cannot close exported pointers exist (#4628)
* fix run_script current working directory (#4629)
* fix pkgs_dirs permissions regression (#4626)

### Non-User-Facing Changes
* fixes for tests when conda-bld directory doesn't exist (#4606)
* use requirements.txt and Makefile for travis-ci setup (#4600, #4633)
* remove hasattr use from compat functions (#4634)


## 4.3.11 (2017-02-09)

### Bug Fixes
* fix attribute error in add_defaults_to_specs (#4577)


## 4.3.10 (2017-02-07)

### Improvements
* remove .json from pickle path (#4498)
* improve empty repodata noarch warning and error messages (#4499)
* don't add python and lua as default specs for private envs (#4529, #4533)
* let default_python be None (#4547, #4550)

### Bug Fixes
* fix #4513 null pointer exception for channel without noarch (#4518)
* fix ssl_verify set type (#4517)
* fix bug for windows multiuser (#4524)
* fix clone with noarch python packages (#4535)
* fix ipv6 for python 2.7 on Windows (#4554)

### Non-User-Facing Changes
* separate integration tests with a marker (#4532)


## 4.3.9 (2017-01-31)

### Improvements
* improve repodata caching for performance (#4478, #4488)
* expand scope of packages included by bad_installed (#4402)
* silence pre-link warning for old noarch (#4451)
* add configuration to optionally require noarch repodata (#4450)
* improve conda subprocessing (#4447)
* respect info/link.json (#4482)

### Bug Fixes
* fix #4398 'hard' was used for link type at one point (#4409)
* fixed "No matches for wildcard '$activate_d/*.fish'" warning (#4415)
* print correct activate/deactivate message for fish shell (#4423)
* fix 'Dist' object has no attribute 'fn' (#4424)
* fix noarch generic and add additional integration test (#4431)
* fix #4425 unknown encoding (#4433)

### Non-User-Facing Changes
* fail CI on conda-build fail (#4405)
* run doctests (#4414)
* make index record mutable again (#4461)
* additional test for conda list --json (#4480)


## 4.3.8 (2017-01-23)

### Bug Fixes
* fix #4309 ignore EXDEV error for directory renames (#4392)
* fix #4393 by force-renaming certain backup files if the path already exists (#4397)


## 4.3.7 (2017-01-20)

### Bug Fixes
* actually revert json output for leaky plan (#4383)
* fix not raising on pre/post-link error (#4382)
* fix find_commands and find_executable for symlinks (#4387)


## 4.3.6 (2017-01-18)

### Bug Fixes
* fix 'Uncaught backoff with errno 41' warning on windows (#4366)
* revert json output for leaky plan (#4349)
* audit os.environ setting (#4360)
* fix #4324 using old dist string instead of dist object (#4361)
* fix #4351 infinite recursion via code in #4120 (#4370)
* fix #4368 conda -h (#4367)
* workaround for symlink race conditions on activate (#4346)


## 4.3.5 (2017-01-17)

### Improvements
* add exception message for corrupt repodata (#4315)

### Bug Fixes
* fix package not being found in cache after download (#4297)
* fix logic for Content-Length mismatch (#4311, #4326)
* use unicode_escape after etag regex instead of utf-8 (#4325)
* fix #4323 central condarc file being ignored (#4327)
* fix #4316 a bug in deactivate (#4316)
* pass target_prefix as env_prefix regardless of is_unlink (#4332)
* pass positional argument 'context' to BasicClobberError (#4335)

### Non-User-Facing Changes
* additional package pinning tests (#4317)


## 4.3.4 (2017-01-13)

### Improvements
* vendor url parsing from urllib3 (#4289)

### Bug Fixes
* fix some bugs in windows multi-user support (#4277)
* fix problems with channels of type <unknown> (#4290)
* include aliases for first command-line argument (#4279)
* fix for multi-line FTP status codes (#4276)

### Non-User-Facing Changes
* make arch in IndexRecord a StringField instead of EnumField
* improve conda-build compatibility (#4266)


## 4.3.3 (2017-01-10)

### Improvements
* respect Cache-Control max-age header for repodata (#4220)
* add 'local_repodata_ttl' configurability (#4240)
* remove questionable "nothing to install" logic (#4237)
* relax channel noarch requirement for 4.3; warn now, raise in future feature release (#4238)
* add additional info to setup.py warning message (#4258)

### Bug Fixes
* remove features properly (#4236)
* do not use `IFS` to find activate/deactivate scripts to source (#4239)
* fix #4235 print message to stderr (#4241)
* fix relative path to python in activate.bat (#4242)
* fix args.channel references (#4245, #4246)
* ensure cache_fn_url right pad (#4255)
* fix #4256 subprocess calls must have env wrapped in str (#4259)


## 4.3.2 (2017-01-06)

### Deprecations/Breaking Changes
* Further refine conda channels specification. To verify if the url of a channel
  represents a valid conda channel, we check that `noarch/repodata.json` and/or
  `noarch/repodata.json.bz2` exist, even if empty. (#3739)

### Improvements
* add new 'path_conflict' and 'clobber' configuration options (#4119)
* separate fetch/extract pass for explicit URLs (#4125)
* update conda homepage to conda.io (#4180)

### Bug Fixes
* fix pre/post unlink/link scripts (#4113)
* fix package version regex and bug in create_link (#4132)
* fix history tracking (#4143)
* fix index creation order (#4131)
* fix #4152 conda env export failure (#4175)
* fix #3779 channel UNC path encoding errors on windows (#4190)
* fix progress bar (#4191)
* use context.channels instead of args.channel (#4199)
* don't use local cached repodata for file:// urls (#4209)

### Non-User-Facing Changes
* xfail anaconda token test if local token is found (#4124)
* fix open-ended test failures relating to python 3.6 release (#4145)
* extend timebomb for test_multi_channel_export (#4169)
* don't unlink dists that aren't in the index (#4130)
* add python 3.6 and new conda-build test targets (#4194)


## 4.3.1 (2016-12-19)

### Improvements
* additional pre-transaction validation (#4090)
* export FileMode enum for conda-build (#4080)
* memoize disk permissions tests (#4091)
* local caching of repodata without remote server calls; new 'repodata_timeout_secs'
  configuration parameter (#4094)
* performance tuning (#4104)
* add additional fields to dist object serialization (#4102)

### Bug Fixes
* fix a noarch install bug on windows (#4071)
* fix a spec mismatch that resulted in python versions getting mixed during packaging (#4079)
* fix rollback linked record (#4092)
* fix #4097 keep split in PREFIX_PLACEHOLDER (#4100)


## 4.3.0 (2016-12-14)  Safety

### New Features
* **Unlink and Link Packages in a Single Transaction**: In the past, conda hasn't always been safe
  and defensive with its disk-mutating actions. It has gleefully clobbered existing files, and
  mid-operation failures leave environments completely broken. In some of the most severe examples,
  conda can appear to "uninstall itself." With this release, the unlinking and linking of packages
  for an executed command is done in a single transaction. If a failure occurs for any reason
  while conda is mutating files on disk, the environment will be returned its previous state.
  While we've implemented some pre-transaction checks (verifying package integrity for example),
  it's impossible to anticipate every failure mechanism. In some circumstances, OS file
  permissions cannot be fully known until an operation is attempted and fails. And conda itself
  is not without bugs. Moving forward, unforeseeable failures won't be catastrophic. (#3833, #4030)

* **Progressive Fetch and Extract Transactions**: Like package unlinking and linking, the
  download and extract phases of package handling have also been given transaction-like behavior.
  The distinction is the rollback on error is limited to a single package. Rather than rolling back
  the download and extract operation for all packages, the single-package rollback prevents the
  need for having to re-download every package if an error is encountered. (#4021, #4030)

* **Generic- and Python-Type Noarch/Universal Packages**: Along with conda-build 2.1.0, a
  noarch/universal type for python packages is officially supported. These are much like universal
  python wheels. Files in a python noarch package are linked into a prefix just like any other
  conda package, with the following additional features
  1. conda maps the `site-packages` directory to the correct location for the python version
     in the environment,
  2. conda maps the python-scripts directory to either $PREFIX/bin or $PREFIX/Scripts depending
     on platform,
  3. conda creates the python entry points specified in the conda-build recipe, and
  4. conda compiles pyc files at install time when prefix write permissions are guaranteed.

  Python noarch packages must be "fully universal."  They cannot have OS- or
  python version-specific dependencies.  They cannot have OS- or python version-specific "scripts"
  files. If these features are needed, traditional conda packages must be used. (#3712)

* **Multi-User Package Caches**: While the on-disk package cache structure has been preserved,
  the core logic implementing package cache handling has had a complete overhaul.  Writable and
  read-only package caches are fully supported. (#4021)

* **Python API Module**: An oft requested feature is the ability to use conda as a python library,
  obviating the need to "shell out" to another python process. Conda 4.3 includes a
  `conda.cli.python_api` module that facilitates this use case. While we maintain the user-facing
  command-line interface, conda commands can be executed in-process. There is also a
  `conda.exports` module to facilitate longer-term usage of conda as a library across conda
  conda releases.  However, conda's python code *is* considered internal and private, subject
  to change at any time across releases. At the moment, conda will not install itself into
  environments other than its original install environment. (#4028)

* **Remove All Locks**:  Locking has never been fully effective in conda, and it often created a
  false sense of security. In this release, multi-user package cache support has been
  implemented for improved safety by hard-linking packages in read-only caches to the user's
  primary user package cache. Still, users are cautioned that undefined behavior can result when
  conda is running in multiple process and operating on the same package caches and/or
  environments. (#3862)

### Deprecations/Breaking Changes
* Conda will refuse to clobber existing files that are not within the unlink instructions of
  the transaction. At the risk of being user-hostile, it's a step forward for conda. We do
  anticipate some growing pains. For example, conda will not clobber packages that have been
  installed with pip (or any other package manager). In other instances, conda packages that
  contain overlapping file paths but are from different package families will not install at
  the same time. The `--force` command line flag is the escape hatch. Using `--force` will
  let your operation proceed, but also makes clear that you want conda to do something it
  considers unsafe.
* Conda signed packages have been removed in 4.3. Vulnerabilities existed. An illusion of security
  is worse than not having the feature at all.  We will be incorporating The Update Framework
  into conda in a future feature release. (#4064)
* Conda 4.4 will drop support for older versions of conda-build.

### Improvements
* create a new "trace" log level enabled by `-v -v -v` or `-vvv` (#3833)
* allow conda to be installed with pip, but only when used as a library/dependency (#4028)
* the 'r' channel is now part of defaults (#3677)
* private environment support for conda (#3988)
* support v1 info/paths.json file (#3927, #3943)
* support v1 info/package_metadata.json (#4030)
* improved solver hint detection, simplified filtering (#3597)
* cache VersionOrder objects to improve performance (#3596)
* fix documentation and typos (#3526, #3572, #3627)
* add multikey configuration validation (#3432)
* some Fish autocompletions (#2519)
* reduce priority for packages removed from the index (#3703)
* add user-agent, uid, gid to conda info (#3671)
* add conda.exports module (#3429)
* make http timeouts configurable (#3832)
* add a pkgs_dirs config parameter (#3691)
* add an 'always_softlink' option (#3870, #3876)
* pre-checks for diskspace, etc for fetch and extract #(4007)
* address #3879 don't print activate message when quiet config is enabled (#3886)
* add zos-z subdir (#4060)
* add elapsed time to HTTP errors (#3942)

### Bug Fixes
* account for the Windows Python 2.7 os.environ unicode aversion (#3363)
* fix link field in record object (#3424)
* anaconda api token bug fix; additional tests (#3673)
* fix #3667 unicode literals and unicode decode (#3682)
* add conda-env entrypoint (#3743)
* fix #3807 json dump on conda config --show --json (#3811)
* fix #3801 location of temporary hard links of index.json (#3813)
* fix invalid yml example (#3849)
* add arm platforms back to subdirs (#3852)
* fix #3771 better error message for assertion errors (#3802)
* fix #3999 spaces in shebang replacement (#4008)
* config --show-sources shouldn't show force by default (#3891)
* fix #3881 don't install conda-env in clones of root (#3899)
* conda-build dist compatibility (#3909)

### Non-User-Facing Changes
* remove unnecessary eval (#3428)
* remove dead install_tar function (#3641)
* apply PEP-8 to conda-env (#3653)
* refactor dist into an object (#3616)
* vendor appdirs; remove conda's dependency on anaconda-client import (#3675)
* revert boto patch from #2380 (#3676)
* move and update ROOT_NO_RM (#3697)
* integration tests for conda clean (#3695, #3699)
* disable coverage on s3 and ftp requests adapters (#3696, #3701)
* github repo hygiene (#3705, #3706)
* major install refactor (#3712)
* remove test timebombs (#4012)
* LinkType refactor (#3882)
* move CrossPlatformStLink and make available as export (#3887)
* make Record immutable (#3965)
* project housekeeping (#3994, #4065)
* context-dependent setup.py files (#4057)


## 4.2.17 (unreleased)

### Improvements
* silence pre-link warning for old noarch 4.2.x backport (#4453)

### Bug Fixes
* remove incorrect elision of delete_prefix_from_linked_data() (#4813)
* fix CB #1825 context clobbering (#4867)
* fix #5101 api->conda regex substitution for Anaconda API channels (#5100)

### Non-User-Facing Changes
* build 4.2.x against conda-build 2.1.2 and enforce passing (#4462)


## 4.2.16 (2017-01-20)

### Improvements
* vendor url parsing from urllib3 (#4289)
* workaround for symlink race conditions on activate (#4346)

### Bug Fixes
* do not replace \ with / in file:// URLs on Windows (#4269)
* include aliases for first command-line argument (#4279)
* fix for multi-line FTP status codes (#4276)
* fix errors with unknown type channels (#4291)
* change sys.exit to raise UpgradeError when info/files not found (#4388)

### Non-User-Facing Changes
* start using doctests in test runs and coverage (#4304)
* additional package pinning tests (#4312)


## 4.2.15 (2017-01-10)

### Improvements
* use 'post' instead of 'dev' for commits according to PEP-440 (#4234)
* do not use IFS to find activate/deactivate scripts to source (#4243)
* fix relative path to python in activate.bat (#4244)

### Bug Fixes
* replace sed with python for activate and deactivate #4257


## 4.2.14 (2017-01-07)

### Improvements
* use install.rm_rf for TemporaryDirectory cleanup (#3425)
* improve handling of local dependency information (#2107)
* add default channels to exports for Windows and Unix (#4103)
* make subdir configurable (#4178)

### Bug Fixes
* fix conda/install.py single-file behavior (#3854)
* fix the api->conda substitution (#3456)
* fix silent directory removal (#3730)
* fix location of temporary hard links of index.json (#3975)
* fix potential errors in multi-channel export and offline clone (#3995)
* fix auxlib/packaging, git hashes are not limited to 7 characters (#4189)
* fix compatibility with requests >=2.12, add pyopenssl as dependency (#4059)
* fix #3287 activate in 4.1-4.2.3 clobbers non-conda PATH changes (#4211)

### Non-User-Facing Changes
* fix open-ended test failures relating to python 3.6 release (#4166)
* allow args passed to cli.main() (#4193, #4200, #4201)
* test against python 3.6 (#4197)


## 4.2.13 (2016-11-22)

### Deprecations/Breaking Changes
* show warning message for pre-link scripts (#3727)
* error and exit for install of packages that require conda minimum version 4.3 (#3726)

### Improvements
* double/extend http timeouts (#3831)
* let descriptive http errors cover more http exceptions (#3834)
* backport some conda-build configuration (#3875)

### Bug Fixes
* fix conda/install.py single-file behavior (#3854)
* fix the api->conda substitution (#3456)
* fix silent directory removal (#3730)
* fix #3910 null check for is_url (#3931)

### Non-User-Facing Changes
* flake8 E116, E121, & E123 enabled (#3883)


## 4.2.12 (2016-11-02)

### Bug Fixes

* fix #3732, #3471, #3744 CONDA_BLD_PATH (#3747)
* fix #3717 allow no-name channels (#3748)
* fix #3738 move conda-env to ruamel_yaml (#3740)
* fix conda-env entry point (#3745 via #3743)
* fix again #3664 trash emptying (#3746)


## 4.2.11 (2016-10-23)

### Improvements
* only try once for windows trash removal (#3698)

### Bug Fixes
* fix anaconda api token bug (#3674)
* fix #3646 FileMode enum comparison (#3683)
* fix #3517 conda install --mkdir (#3684)
* fix #3560 hack anaconda token coverup on conda info (#3686)
* fix #3469 alias envs_path to envs_dirs (#3685)


## 4.2.10 (2016-10-18)

### Improvements
* add json output for `conda info -s` (#3588)
* ignore certain binary prefixes on windows (#3539)
* allow conda config files to have .yaml extensions or 'condarc' anywhere in filename (#3633)

### Bug Fixes
* fix conda-build's handle_proxy_407 import (#3666)
* fix #3442, #3459, #3481, #3531, #3548 multiple networking and auth issues (#3550)
* add back linux-ppc64le subdir support (#3584)
* fix #3600 ensure links are removed when unlinking (#3625)
* fix #3602 search channels by platform (#3629)
* fix duplicated packages when updating environment (#3563)
* fix #3590 exception when parsing invalid yaml (#3593 via #3634)
* fix #3655 a string decoding error (#3656)

### Non-User-Facing Changes
* backport conda.exports module to 4.2.x (#3654)
* travis-ci OSX fix (#3615 via #3657)


## 4.2.9 (2016-09-27)

### Bug Fixes
* fix #3536 conda-env messaging to stdout with --json flag (#3537)
* fix #3525 writing to sys.stdout with --json flag for post-link scripts (#3538)
* fix #3492 make NULL falsey with python 3 (#3524)


## 4.2.8 (2016-09-26)

### Improvements
* add "error" key back to json error output (#3523)

### Bug Fixes
* fix #3453 conda fails with create_default_packages (#3454)
* fix #3455 --dry-run fails (#3457)
* dial down error messages for rm_rf (#3522)
* fix #3467 AttributeError encountered for map config parameter validation (#3521)


## 4.2.7 (2016-09-16)

### Deprecations/Breaking Changes
* revert to 4.1.x behavior of `conda list --export` (#3450, #3451)

### Bug Fixes
* don't add binstar token if it's given in the channel spec (#3427, #3440, #3444)
* fix #3433 failure to remove broken symlinks (#3436)

### Non-User-Facing Changes
* use install.rm_rf for TemporaryDirectory cleanup (#3425)


## 4.2.6 (2016-09-14)

### Improvements
* add support for client TLS certificates (#3419)
* address #3267 allow migration of channel_alias (#3410)
* conda-env version matches conda version (#3422)

### Bug Fixes
* fix #3409 unsatisfiable dependency error message (#3412)
* fix #3408 quiet rm_rf (#3413)
* fix #3407 padding error messaging (#3416)
* account for the Windows Python 2.7 os.environ unicode aversion (#3363 via #3420)


## 4.2.5 (2016-09-08)

### Deprecations/Breaking Changes
* partially revert #3041 giving conda config --add previous --prepend behavior (#3364 via #3370)
* partially revert #2760 adding back conda package command (#3398)

### Improvements
* order output of conda config --show; make --json friendly (#3384 via #3386)
* clean the pid based lock on exception (#3325)
* improve file removal on all platforms (#3280 via #3396)

### Bug Fixes
* fix #3332 allow download urls with :: in them (#3335)
* fix always_yes and not-set argparse args overriding other sources (#3374)
* fix ftp fetch timeout (#3392)
* fix #3307 add try/except block for touch lock (#3326)
* fix CONDA_CHANNELS environment variable splitting (#3390)
* fix #3378 CONDA_FORCE_32BIT environment variable (#3391)
* make conda info channel urls actually give urls (#3397)
* fix cio_test compatibility (#3395 via #3400)


## 4.2.4 (2016-08-18)

### Bug Fixes
* fix #3277 conda list package order (#3278)
* fix channel priority issue with duplicated channels (#3283)
* fix local channel channels; add full conda-build unit tests (#3281)
* fix conda install with no package specified (#3284)
* fix #3253 exporting and importing conda environments (#3286)
* fix priority messaging on conda config --get (#3304)
* fix conda list --export; additional integration tests (#3291)
* fix conda update --all idempotence; add integration tests for channel priority (#3306)

### Non-User-Facing Changes
* additional conda-env integration tests (#3288)


## 4.2.3 (2016-08-11)

### Improvements
* added zsh and zsh.exe to Windows shells (#3257)

### Bug Fixes
* allow conda to downgrade itself (#3273)
* fix breaking changes to conda-build from 4.2.2 (#3265)
* fix empty environment issues with conda and conda-env (#3269)

### Non-User-Facing Changes
* add integration tests for conda-env (#3270)
* add more conda-build smoke tests (#3274)


## 4.2.2 (2016-08-09)

### Improvements
* enable binary prefix replacement on windows (#3262)
* add `--verbose` command line flag (#3237)
* improve logging and exception detail (#3237, #3252)
* do not remove empty environment without asking; raise an error when a named environment
  can't be found (#3222)

### Bug Fixes
* fix #3226 user condarc not available on Windows (#3228)
* fix some bugs in conda config --show* (#3212)
* fix conda-build local channel bug (#3202)
* remove subprocess exiting message (#3245)
* fix comment parsing and channels in conda-env environment.yml (#3258, #3259)
* fix context error with conda-env (#3232)
* fix #3182 conda install silently skipping failed linking (#3184)


## 4.2.1 (2016-08-01)

### Improvements
* improve an error message that can happen during conda install --revision (#3181)
* use clean sys.exit with user choice 'No' (#3196)

### Bug Fixes
* critical fix for 4.2.0 error when no git is on PATH (#3193)
* revert #3171 lock cleaning on exit pending further refinement
* patches for conda-build compatibility with 4.2 (#3187)
* fix a bug in --show-sources output that ignored aliased parameter names (#3189)

### Non-User-Facing Changes
* move scripts in bin to shell directory (#3186)


## 4.2.0 (2016-07-28)  Configuration

### New Features
* **New Configuration Engine**: Configuration and "operating context" are the foundation of
  conda's functionality. Conda now has the ability to pull configuration information from a
  multitude of on-disk locations, including `.d` directories and a `.condarc` file *within*
  a conda environment), along with full `CONDA_` environment variable support. Helpful
  validation errors are given for improperly-specified configuration. Full documentation
  updates pending. (#2537, #3160, #3178)
* **New Exception Handling Engine**: Previous releases followed a pattern of premature exiting
  (with hard calls to `sys.exit()` when exceptional circumstances were encountered. This
  release replaces over 100 `sys.exit` calls with python exceptions.  For conda developers,
  this will result in tests that are easier to write.  For developers using conda, this is a
  first step on a long path toward conda being directly importable.  For conda users, this will
  eventually result in more helpful and descriptive errors messages.
  (#2899, #2993, #3016, #3152, #3045)
* **Empty Environments**: Conda can now create "empty" environments when no initial packages
  are specified, alleviating a common source of confusion. (#3072, #3174)
* **Conda in Private Env**: Conda can now be configured to live within its own private
  environment.  While it's not yet default behavior, this represents a first step toward
  separating the `root` environment into a "conda private" environment and a "user default"
  environment. (#3068)
* **Regex Version Specification**: Regular expressions are now valid version specifiers.
  For example, `^1\.[5-8]\.1$|2.2`. (#2933)

### Deprecations/Breaking Changes
* remove conda init (#2759)
* remove conda package and conda bundle (#2760)
* deprecate conda-env repo; pull into conda proper (#2950, #2952, #2954, #3157, #3163, #3170)
* force use of ruamel_yaml (#2762)
* implement conda config --prepend; change behavior of --add to --append (#3041)
* exit on link error instead of logging it (#2639)

### Improvements
* improve locking (#2962, #2989, #3048, #3075)
* clean up requests usage for fetching packages (#2755)
* remove excess output from conda --help (#2872)
* remove os.remove in update_prefix (#3006)
* better error behavior if conda is spec'd for a non-root environment (#2956)
* scale back try_write function on unix (#3076)

### Bug Fixes
* remove psutil requirement, fixes annoying error message (#3135, #3183)
* fix #3124 add threading lock to memoize (#3134)
* fix a failure with multi-threaded repodata downloads (#3078)
* fix windows file url (#3139)
* address #2800, error with environment.yml and non-default channels (#3164)

### Non-User-Facing Changes
* project structure enhancement (#2929, #3132, #3133, #3136)
* clean up channel handling with new channel model (#3130, #3151)
* add Anaconda Cloud / Binstar auth handler (#3142)
* remove dead code (#2761, #2969)
* code refactoring and additional tests (#3052, #3020)
* remove auxlib from project root (#2931)
* vendor auxlib 0.0.40 (#2932, #2943, #3131)
* vendor toolz 0.8.0 (#2994)
* move progressbar to vendor directory (#2951)
* fix conda.recipe for new quirks with conda-build (#2959)
* move captured function to common module (#3083)
* rename CHANGELOG to md (#3087)


## 4.1.13 (unreleased)

* improve handling of local dependency information, #2107
* show warning message for pre-link scripts, #3727
* error and exit for install of packages that require conda minimum version 4.3, #3726
* fix conda/install.py single-file behavior, #3854
* fix open-ended test failures relating to python 3.6 release, #4167
* fix #3287 activate in 4.1-4.2.3 clobbers non-conda PATH changes, #4211
* fix relative path to python in activate.bat, #4244


## 4.1.12 (2016-09-08)

* fix #2837 "File exists" in symlinked path with parallel activations, #3210
* fix prune option when installing packages, #3354
* change check for placeholder to be more friendly to long PATH, #3349


## 4.1.11 (2016-07-26)

* fix PS1 backup in activate script, #3135 via #3155
* correct resolution for 'handle failures in binstar_client more generally', #3156


## 4.1.10 (2016-07-25)

* ignore symlink failure because of read-only file system, #3055
* backport shortcut tests, #3064
* fix #2979 redefinition of $SHELL variable, #3081
* fix #3060 --clone root --copy exception, #3080


## 4.1.9 (2016-07-20)

* fix #3104, add global BINSTAR_TOKEN_PAT
* handle failures in binstar_client more generally


## 4.1.8 (2016-07-12)

* fix #3004 UNAUTHORIZED for url (null binstar token), #3008
* fix overwrite existing redirect shortcuts when symlinking envs, #3025
* partially revert no default shortcuts, #3032, #3047


## 4.0.11 2016-07-09

* allow auto_update_conda from sysrc, #3015 via #3021


## 4.1.7 (2016-07-07)

* add msys2 channel to defaults on Windows, #2999
* fix #2939 channel_alias issues; improve offline enforcement, #2964
* fix #2970, #2974 improve handling of file:// URLs inside channel, #2976


## 4.1.6 (2016-07-01)

* slow down exp backoff from 1 ms to 100 ms factor, #2944
* set max time on exp_backoff to ~6.5 sec,#2955
* fix #2914 add/subtract from PATH; kill folder output text, #2917
* normalize use of get_index behavior across clone/explicit, #2937
* wrap root prefix check with normcase, #2938


## 4.1.5 (2016-06-29)

* more conservative auto updates of conda #2900
* fix some permissions errors with more aggressive use of move_path_to_trash, #2882
* fix #2891 error if allow_other_channels setting is used, #2896
* fix #2886, #2907 installing a tarball directly from the package cache, #2908
* fix #2681, #2778 reverting #2320 lock behavior changes, #2915


## 4.0.10 (2016-06-29)

* fix #2846 revert the use of UNC paths; shorten trash filenames, #2859 via #2878
* fix some permissions errors with more aggressive use of move_path_to_trash, #2882 via #2894


## 4.1.4 (2016-06-27)

* fix #2846 revert the use of UNC paths; shorten trash filenames, #2859
* fix exp backoff on Windows, #2860
* fix #2845 URL for local file repos, #2862
* fix #2764 restore full path var on win; create to CONDA_PREFIX env var, #2848
* fix #2754 improve listing pip installed packages, #2873
* change root prefix detection to avoid clobbering root activate scripts, #2880
* address #2841 add lowest and highest priority indication to channel config output, #2875
* add SYMLINK_CONDA to planned instructions, #2861
* use CONDA_PREFIX, not CONDA_DEFAULT_ENV for activate.d, #2856
* call scripts with redirect on win; more error checking to activate, #2852


## 4.1.3 (2016-06-23)

* ensure conda-env auto update, along with conda, #2772
* make yaml booleans behave how everyone expects them to, #2784
* use accept-encoding for repodata; prefer repodata.json to repodata.json.bz2, #2821
* additional integration and regression tests, #2757, #2774, #2787
* add offline mode to printed info; use offline flag when grabbing channels, #2813
* show conda-env version in conda info, #2819
* adjust channel priority superseded list, #2820
* support epoch ! characters in command line specs, #2832
* accept old default names and new ones when canonicalizing channel URLs #2839
* push PATH, PS1 manipulation into shell scripts, #2796
* fix #2765 broken source activate without arguments, #2806
* fix standalone execution of install.py, #2756
* fix #2810 activating conda environment broken with git bash on Windows, #2795
* fix #2805, #2781 handle both file-based channels and explicit file-based URLs, #2812
* fix #2746 conda create --clone of root, #2838
* fix #2668, #2699 shell recursion with activate #2831


## 4.1.2 (2016-06-17)

* improve messaging for "downgrades" due to channel priority, #2718
* support conda config channel append/prepend, handle duplicates, #2730
* remove --shortcuts option to internal CLI code, #2723
* fix an issue concerning space characters in paths in activate.bat, #2740
* fix #2732 restore yes/no/on/off for booleans on the command line, #2734
* fix #2642 tarball install on Windows, #2729
* fix #2687, #2697 WindowsError when creating environments on Windows, #2717
* fix #2710 link instruction in conda create causes TypeError, #2715
* revert #2514, #2695, disabling of .netrc files, #2736
* revert #2281 printing progress bar to terminal, #2707


## 4.1.1 (2016-06-16)

* add auto_update_conda config parameter, #2686
* fix #2669 conda config --add channels can leave out defaults, #2670
* fix #2703 ignore activate symlink error if links already exist, #2705
* fix #2693 install duplicate packages with older version of Anaconda, #2701
* fix #2677 respect HTTP_PROXY, #2695
* fix #2680 broken fish integration, #2685, #2694
* fix an issue with conda never exiting, #2689
* fix #2688 explicit file installs, #2708
* fix #2700 conda list UnicodeDecodeError, #2706


## 4.0.9 (2016-06-15)

* add auto_update_conda config parameter, #2686


## 4.1.0 (2016-06-14)  Channel Priority

* clean up activate and deactivate scripts, moving back to conda repo, #1727,
  #2265, #2291, #2473, #2501, #2484
* replace pyyaml with ruamel_yaml, #2283, #2321
* better handling of channel collisions, #2323, #2369 #2402, #2428
* improve listing of pip packages with conda list, #2275
* re-license progressbar under BSD 3-clause, #2334
* reduce the amount of extraneous info in hints, #2261
* add --shortcuts option to install shortcuts on windows, #2623
* skip binary replacement on windows, #2630
* don't show channel urls by default in conda list, #2282
* package resolution and solver tweaks, #2443, #2475, #2480
* improved version & build matching, #2442, #2488
* print progress to the terminal rather than stdout, #2281
* verify version specs given on command line are valid, #2246
* fix for try_write function in case of odd permissions, #2301
* fix a conda search --spec error, #2343
* update User-Agent for conda connections, #2347
* remove some dead code paths, #2338, #2374
* fixes a thread safety issue with http requests, #2377, #2383
* manage BeeGFS hard-links non-POSIX configuration, #2355
* prevent version downgrades during removes, #2394
* fix conda info --json, #2445
* truncate shebangs over 127 characters using /usr/bin/env, #2479
* extract packages to a temporary directory then rename, #2425, #2483
* fix help in install, #2460
* fix re-install bug when sha1 differs, #2507
* fix a bug with file deletion, #2499
* disable .netrc files, #2514
* dont fetch index on remove --all, #2553
* allow track_features to be a string *or* a list in .condarc, #2541
* fix #2415 infinite recursion in invalid_chains, #2566
* allow channel_alias to be different than binstar, #2564


## 4.0.8 (2016-06-03)

* fix a potential problem with moving files to trash, #2587


## 4.0.7 (2016-05-26)

* workaround for boto bug, #2380


## 4.0.6 (2016-05-11)

* log "custom" versions as updates rather than downgrades, #2290
* fixes a TypeError exception that can occur on install/update, #2331
* fixes an error on Windows removing files with long path names, #2452


## 4.0.5 (2016-03-16)

* improved help documentation for install, update, and remove, #2262
* fixes #2229 and #2250 related to conda update errors on Windows, #2251
* fixes #2258 conda list for pip packages on Windows, #2264


## 4.0.4 (2016-03-10)

* revert #2217 closing request sessions, #2233


## 4.0.3 (2016-03-10)

* adds a `conda clean --all` feature, #2211
* solver performance improvements, #2209
* fixes conda list for pip packages on windows, #2216
* quiets some logging for package downloads under python 3, #2217
* more urls for `conda list --explicit`, #1855
* prefer more "latest builds" for more packages, #2227
* fixes a bug with dependency resolution and features, #2226


## 4.0.2 (2016-03-08)

* fixes track_features in ~/.condarc being a list, see also #2203
* fixes incorrect path in lock file error #2195
* fixes issues with cloning environments, #2193, #2194
* fixes a strange interaction between features and versions, #2206
* fixes a bug in low-level SAT clause generation creating a
  preference for older versions, #2199


## 4.0.1 (2016-03-07)

* fixes an install issue caused by md5 checksum mismatches, #2183
* remove auxlib build dependency, #2188


## 4.0.0 (2016-03-04)  Solver

* The solver has been retooled significantly. Performance
  should be improved in most circumstances, and a number of issues
  involving feature conflicts should be resolved.
* `conda update <package>` now handles dependencies properly
  according to the setting of the "update_deps" configuration:
      --update-deps: conda will also update any dependencies as needed
                     to install the latest version of the requested
                     packages.  The minimal set of changes required to
                     achieve this is sought.
      --no-update-deps: conda will update the packages *only* to the
                     extent that no updates to the dependencies are
                     required
  The previous behavior, which would update the packages without regard to
  their dependencies, could result in a broken configuration, and has been
  removed.
* Conda finally has an official logo.
* Fix `conda clean --packages` on Windows, #1944
* Conda sub-commands now support dashes in names, #1840


## 3.19.4 (unreleased)

* improve handling of local dependency information, #2107
* use install.rm_rf for TemporaryDirectory cleanup, #3425
* fix the api->conda substitution, #3456
* error and exit for install of packages that require conda minimum version 4.3, #3726
* show warning message for pre-link scripts, #3727
* fix silent directory removal, #3730
* fix conda/install.py single-file behavior, #3854


## 3.19.3 (2016-02-19)

* fix critical issue, see #2106

## 3.19.2 (2016-02-19)

* add basic activate/deactivate, conda activate/deactivate/ls for fish,
  see #545
* remove error when CONDA_FORCE_32BIT is set on 32-bit systems, #1985
* suppress help text for --unknown option, #2051
* fix issue with conda create --clone post-link scripts, #2007
* fix a permissions issue on windows, #2083

## 3.19.1 (2016-02-01)

* resolve.py: properly escape periods in version numbers, #1926
* support for pinning Lua by default, #1934
* remove hard-coded test URLs, a module cio_test is now expected when
  CIO_TEST is set


## 3.19.0 (2015-12-17)

* OpenBSD 5.x support, #1891
* improve install CLI to make Miniconda -f work, #1905


## 3.18.9 (2015-12-10)

* allow chaining default_channels (only applies to "system" condarc), from
  from CLI, #1886
* improve default for --show-channel-urls in conda list, #1900


## 3.18.8 (2015-12-03)

* always attempt to delete files in rm_rf, #1864


## 3.18.7 (2015-12-02)

* simplify call to menuinst.install()
* add menuinst as dependency on Windows
* add ROOT_PREFIX to post-link (and pre_unlink) environment


## 3.18.6 (2015-11-19)

* improve conda clean when user lacks permissions, #1807
* make show_channel_urls default to True, #1771
* cleaner write tests, #1735
* fix documentation, #1709
* improve conda clean when directories don't exist, #1808


## 3.18.5 (2015-11-11)

* fix bad menuinst exception handling, #1798
* add workaround for unresolved dependencies on Windows

## 3.18.4 (2015-11-09)

* allow explicit file to contain MD5 hashsums
* add --md5 option to "conda list --explicit"
* stop infinite recursion during certain resolve operations, #1749
* add dependencies even if strictness == 3, #1766


## 3.18.3 (2015-10-15)

* added a pruning step for more efficient solves, #1702
* disallow conda-env to be installed into non-root environment
* improve error output for bad command input, #1706
* pass env name and setup cmd to menuinst, #1699


## 3.18.2 (2015-10-12)

* add "conda list --explicit" which contains the URLs of all conda packages
  to be installed, and can used with the install/create --file option, #1688
* fix a potential issue in conda clean
* avoid issues with LookupErrors when updating Python in the root
  environment on Windows
* don't fetch the index from the network with conda remove
* when installing conda packages directly, "conda install <pkg>.tar.bz2",
  unlink any installed package with that name (not just the installed one)
* allow menu items to be installed in non-root env, #1692


## 3.18.1 (2015-09-28)

* fix: removed reference to win_ignore_root in plan module


## 3.18.0 (2015-09-28)

* allow Python to be updated in root environment on Windows, #1657
* add defaults to specs after getting pinned specs (allows to pin a
  different version of Python than what is installed)
* show what older versions are in the solutions in the resolve debug log
* fix some issues with Python 3.5
* respect --no-deps when installing from .tar or .tar.bz2
* avoid infinite recursion with NoPackagesFound and conda update --all --file
* fix conda update --file
* toposort: Added special case to remove 'pip' dependency from 'python'
* show dotlog messages during hint generation with --debug
* disable the max_only heuristic during hint generation
* new version comparison algorithm, which consistently compares any version
  string, and better handles version strings using things like alpha, beta,
  rc, post, and dev. This should remove any inconsistent version comparison
  that would lead to conda installing an incorrect version.
* use the trash in rm_rf, meaning more things will get the benefit of the
  trash system on Windows
* add the ability to pass the --file argument multiple times
* add conda upgrade alias for conda update
* add update_dependencies condarc option and --update-deps/--no-update-deps
  command line flags
* allow specs with conda update --all
* add --show-channel-urls and --no-show-channel-urls command line options
* add always_copy condarc option
* conda clean properly handles multiple envs directories. This breaks
  backwards compatibility with some of the --json output. Some of the old
  --json keys are kept for backwards compatibility.


## 3.17.0 (2015-09-11)

* add windows_forward_slashes option to walk_prefix(), see #1513
* add ability to set CONDA_FORCE_32BIT environment variable, it should
  should only be used when running conda-build, #1555
* add config option to makes the python dependency on pip optional, #1577
* fix an UnboundLocalError
* print note about pinned specs in no packages found error
* allow wildcards in AND-connected version specs
* print pinned specs to the debug log
* fix conda create --clone with create_default_packages
* give a better error when a proxy isn't found for a given scheme
* enable running 'conda run' in offline mode
* fix issue where hardlinked cache contents were being overwritten
* correctly skip packages whose dependencies can't be found with conda
  update --all
* use clearer terminology in -m help text.
* use splitlines to break up multiple lines throughout the codebase
* fix AttributeError with SSLError


## 3.16.0 (2015-08-10)

  * rename binstar -> anaconda, see #1458
  * fix --use-local when the conda-bld directory doesn't exist
  * fixed --offline option when using "conda create --clone", see #1487
  * don't mask recursion depth errors
  * add conda search --reverse-dependency
  * check whether hardlinking is available before linking when
    using "python install.py --link" directly, see #1490
  * don't exit nonzero when installing a package with no dependencies
  * check which features are installed in an environment via track_features,
    not features
  * set the verify flag directly on CondaSession (fixes conda skeleton not
    respecting the ssl_verify option)


## 3.15.1 (2015-07-23)

  * fix conda with older versions of argcomplete
  * restore the --force-pscheck option as a no-op for backwards
    compatibility


## 3.15.0 (2015-07-22)

  * sort the output of conda info package correctly
  * enable tab completion of conda command extensions using
    argcomplete. Command extensions that import conda should use
    conda.cli.conda_argparse.ArgumentParser instead of
    argparse.ArgumentParser. Otherwise, they should enable argcomplete
    completion manually.
  * allow psutil and pycosat to be updated in the root environment on Windows
  * remove all mentions of pscheck. The --force-pscheck flag has been removed.
  * added support for S3 channels
  * fix color issues from pip in conda list on Windows
  * add support for other machine types on Linux, in particular ppc64le
  * add non_x86_linux_machines set to config module
  * allow ssl_verify to accept strings in addition to boolean values in condarc
  * enable --set to work with both boolean and string values


## 3.14.1 (2015-06-29)

  * make use of Crypto.Signature.PKCS1_PSS module, see #1388
  * note when features are being used in the unsatisfiable hint


## 3.14.0 (2015-06-16)

  * add ability to verify signed packages, see #1343 (and conda-build #430)
  * fix issue when trying to add 'pip' dependency to old python packages
  * provide option "conda info --unsafe-channels" for getting unobscured
    channel list, #1374


## 3.13.0 (2015-06-04)

  * avoid the Windows file lock by moving files to a trash directory, #1133
  * handle env dirs not existing in the Environments completer
  * rename binstar.org -> anaconda.org, see #1348
  * speed up 'source activate' by ~40%


## 3.12.0 (2015-05-05)

  * correctly allow conda to update itself
  * print which file leads to the "unable to remove file" error on Windows
  * add support for the no_proxy environment variable, #1171
  * add a much faster hint generation for unsatisfiable packages, which is now
    always enabled (previously it would not run if there were more than ten
    specs). The new hint only gives one set of conflicting packages, rather
    than all sets, so multiple passes may be necessary to fix such issues
  * conda extensions that import conda should use
    conda.cli.conda_argparser.ArgumentParser instead of
    argparse.ArgumentParser to conform to the conda help guidelines (e.g., all
    help messages should be capitalized with periods, and the options should
    be preceded by "Options:" for the sake of help2man).
  * add confirmation dialog to conda remove. Fixes conda remove --dry-run.


## 3.11.0 (2015-04-22)

  * fix issue where forced update on Windows could cause a package to break
  * remove detection of running processes that might conflict
  * deprecate --force-pscheck (now a no-op argument)
  * make conda search --outdated --names-only work, fixes #1252
  * handle the history file not having read or write permissions better
  * make multiple package resolutions warning easier to read
  * add --full-name to conda list
  * improvements to command help


## 3.10.1 (2015-04-06)

  * fix logic in @memoized for unhashable args
  * restored json cache of repodata, see #1249
  * hide binstar tokens in conda info --json
  * handle CIO_TEST='2 '
  * always find the solution with minimal number of packages, even if there
    are many solutions
  * allow comments at the end of the line in requirement files
  * don't update the progressbar until after the item is finished running
  * add conda/<version> to HTTP header User-Agent string


## 3.10.0 (2015-03-12)

  * change default repo urls to be https
  * add --offline to conda search
  * add --names-only and --full-name to conda search
  * add tab completion for packages to conda search


## 3.9.1 (2015-02-24)

  * pscheck: check for processes in the current environment, see #1157
  * don't write to the history file if nothing has changed, see #1148
  * conda update --all installs packages without version restrictions (except
    for Python), see #1138
  * conda update --all ignores the anaconda metapackage, see #1138
  * use forward slashes for file urls on Windows
  * don't symlink conda in the root environment from activate
  * use the correct package name in the progress bar info
  * use json progress bars for unsatisfiable dependencies hints
  * don't let requests decode gz files when downloaded


## 3.9.0 (2015-02-16)

  * remove (de)activation scripts from conda, those are now in conda-env
  * pip is now always added as a Python dependency
  * allow conda to be installed into environments which start with _
  * add argcomplete tab completion for environments with the -n flag, and for
    package names with install, update, create, and remove


## 3.8.4 (2015-02-03)

  * copy (de)activate scripts from conda-env
  * Add noarch (sub) directory support


## 3.8.3 (2015-01-28)

  * simplified how ROOT_PREFIX is obtained in (de)activate


## 3.8.2 (2015-01-27)

  * add conda clean --source-cache to clean the conda build source caches
  * add missing quotes in (de)activate.bat, fixes problem in Windows when
    conda is installed into a directory with spaces
  * fix conda install --copy


## 3.8.1 (2015-01-23)

  * add missing utf-8 decoding, fixes Python 3 bug when icondata to json file


## 3.8.0 (2015-01-22)

  * move active script into conda-env, which is now a new dependency
  * load the channel urls in the correct order when using concurrent.futures
  * add optional 'icondata' key to json files in conda-meta directory, which
    contain the base64 encoded png file or the icon
  * remove a debug print statement


## 3.7.4 (2014-12-18)

  * add --offline option to install, create, update and remove commands, and
    also add ability to set "offline: True" in condarc file
  * add conda uninstall as alias for conda remove
  * add conda info --root
  * add conda.pip module
  * fix CONDARC pointing to non-existing file, closes issue #961
  * make update -f work if the package is already up-to-date
  * fix possible TypeError when printing an error message
  * link packages in topologically sorted order (so that pre-link scripts can
    assume that the dependencies are installed)
  * add --copy flag to install
  * prevent the progressbar from crashing conda when fetching in some
    situations


## 3.7.3 (2014-11-05)

  * conda install from a local conda package (or a tar fill which
    contains conda packages), will now also install the dependencies
    listed by the installed packages.
  * add SOURCE_DIR environment variable in pre-link subprocess
  * record all created environments in ~/.conda/environments.txt


## 3.7.2 (2014-10-31)

  * only show the binstar install message once
  * print the fetching repodata dot after the repodata is fetched
  * write the install and remove specs to the history file
  * add '-y' as an alias to '--yes'
  * the `--file` option to conda config now defaults to
    os.environ.get('CONDARC')
  * some improvements to documentation (--help output)
  * add user_rc_path and sys_rc_path to conda info --json
  * cache the proxy username and password
  * avoid warning about conda in pscheck
  * make ~/.conda/envs the first user envs dir


## 3.7.1 (2014-10-07)

  * improve error message for forgetting to use source with activate and
    deactivate, see issue #601
  * don't allow to remove the current environment, see issue #639
  * don't fail if binstar_client can't be imported for other reasons,
    see issue #925
  * allow spaces to be contained in conda run
  * only show the conda install binstar hint if binstar is not installed
  * conda info package_spec now gives detailed info on packages. conda info
    path has been removed, as it is duplicated by conda package -w path.


## 3.7.0 (2014-09-19)

  * faster algorithm for --alt-hint
  * don't allow channel_alias with allow_other_channels: false if it is set in
    the system .condarc
  * don't show long "no packages found" error with update --all
  * automatically add the Binstar token to urls when the binstar client is
    installed and logged in
  * carefully avoid showing the binstar token or writing it to a file
  * be more careful in conda config about keys that are the wrong type
  * don't expect directories starting with conda- to be commands
  * no longer recommend to run conda init after pip installing conda. A pip
    installed conda will now work without being initialized to create and
    manage other environments
  * the rm function on Windows now works around access denied errors
  * fix channel urls now showing with conda list with show_channel_urls set to
    true


## 3.6.4 (2014-09-08)

  * fix removing packages that aren't in the channels any more
  * Pretties output for --alt-hint


## 3.6.3 (2014-09-04)

  * skip packages that can't be found with update --all
  * add --use-local to search and remove
  * allow --use-local to be used along with -c (--channels) and
    --override-channels. --override-channels now requires either -c or
    --use-local
  * allow paths in has_prefix to be quoted, to allow for spaces in paths on
    Windows
  * retain Unix style path separators for prefixes in has_prefix on
    Windows (if the placeholder path uses /, replace it with a path that uses
    /, not \)
  * fix bug in --use-local due to API changes in conda-build
  * include user site directories in conda info -s
  * make binary has_prefix replacement work with spaces after the prefix
  * make binary has_prefix replacement replace multiple occurrences of the
    placeholder in the same null-terminated string
  * don't show packages from other platforms as installed or cached in conda
    search
  * be more careful about not warning about conda itself in pscheck
  * Use a progress bar for the unsatisfiable packages hint generation
  * Don't use TemporaryFile in try_write, as it is too slow when it fails
  * Ignore InsecureRequestWarning when ssl_verify is False
  * conda remove removes features tracked by removed packages in
    track_features


## 3.6.2 (2014-08-20)

  * add --use-index-cache to conda remove
  * fix a bug where features (like mkl) would be selected incorrectly
  * use concurrent.future.ThreadPool to fetch package metadata asynchronously
    in Python 3.
  * do the retries in rm_rf on every platform
  * use a higher cutoff for package name misspellings
  * allow changing default channels in "system" .condarc


## 3.6.1 (2014-08-13)

  * add retries to download in fetch module
  * improved error messages for missing packages
  * more robust rm_rf on Windows
  * print multiline help for subcommands correctly


## 3.6.0 (2014-08-11)

  * correctly check if a package can be hard-linked if it isn't extracted yet
  * change how the package plan is printed to better show what is new,
    updated, and downgraded
  * use suggest_normalized_version in the resolve module. Now versions like
    1.0alpha that are not directly recognized by verlib's NormalizedVersion
    are supported better
  * conda run command, to run apps and commands from packages
  * more complete --json API. Every conda command should fully support --json
    output now.
  * show the conda_build and requests versions in conda info
  * include packages from setup.py develop in conda list (with use_pip)
  * raise a warning instead of dying when the history file is invalid
  * use urllib.quote on the proxy password
  * make conda search --outdated --canonical work
  * pin the Python version during conda init
  * fix some metadata that is written for Python during conda init
  * allow comments in a pinned file
  * allow installing and updating menuinst on Windows
  * allow conda create with both --file and listed packages
  * better handling of some nonexistent packages
  * fix command line flags in conda package
  * fix a bug in the ftp adapter


## 3.5.5 (2014-06-10)

  * remove another instance pycosat version detection, which fails on
    Windows, see issue #761


## 3.5.4 (2014-06-10)

  * remove pycosat version detection, which fails on Windows, see issue #761


## 3.5.3 (2014-06-09)

  * fix conda update to correctly not install packages that are already
    up-to-date
  * always fail with connection error in download
  * the package resolution is now much faster and uses less memory
  * add ssl_verify option in condarc to allow ignoring SSL certificate
    verification, see issue #737


## 3.5.2 (2014-05-27)

  * fix bug in activate.bat and deactivate.bat on Windows


## 3.5.1 (2014-05-26)

  * fix proxy support - conda now prompts for proxy username and password
    again
  * fix activate.bat on Windows with spaces in the path
  * update optional psutil dependency was updated to psutil 2.0 or higher


## 3.5.0 (2014-05-15)

  * replace use of urllib2 with requests. requests is now a hard dependency of
    conda.
  * add ability to only allow system-wise specified channels
  * hide binstar from output of conda info


## 3.4.3 (2014-05-05)

  * allow prefix replacement in binary files, see issue #710
  * check if creating hard link is possible and otherwise copy,
    during install
  * allow circular dependencies


## 3.4.2 (2014-04-21)

  * conda clean --lock: skip directories that don't exist, fixes #648
  * fixed empty history file causing crash, issue #644
  * remove timezone information from history file, fixes issue #651
  * fix PackagesNotFound error for missing recursive dependencies
  * change the default for adding cache from the local package cache -
    known is now the default and the option to use index metadata from the
    local package cache is --unknown
  * add --alt-hint as a method to get an alternate form of a hint for
    unsatisfiable packages
  * add conda package --ls-files to list files in a package
  * add ability to pin specs in an environment. To pin a spec, add a file
    called pinned to the environment's conda-meta directory with the specs to
    pin. Pinned specs are always kept installed, unless the --no-pin flag is
    used.
  * fix keyboard interrupting of external commands. Now keyboard interrupting
    conda build correctly removes the lock file
  * add no_link ability to conda, see issue #678


## 3.4.1 (2014-04-07)

  * always use a pkgs cache directory associated with an envs directory, even
    when using -p option with an arbitrary a prefix which is not inside an
    envs dir
  * add setting of PYTHONHOME to conda info --system
  * skip packages with bad metadata


## 3.4.0 (2014-04-02)

  * added revision history to each environment:
      - conda list --revisions
      - conda install --revision
      - log is stored in conda-meta/history
  * allow parsing pip-style requirement files with --file option and in command
    line arguments, e.g. conda install 'numpy>=1.7', issue #624
  * fix error message for --file option when file does not exist
  * allow DEFAULTS in CONDA_ENVS_PATH, which expands to the defaults settings,
    including the condarc file
  * don't install a package with a feature (like mkl) unless it is
    specifically requested (i.e., that feature is already enabled in that
    environment)
  * add ability to show channel URLs when displaying what is going to be
    downloaded by setting "show_channel_urls: True" in condarc
  * fix the --quiet option
  * skip packages that have dependencies that can't be found


## 3.3.2 (2014-03-24)

  * fix the --file option
  * check install arguments before fetching metadata
  * fix a printing glitch with the progress bars
  * give a better error message for conda clean with no arguments
  * don't include unknown packages when searching another platform


## 3.3.1 (2014-03-19)

  * Fix setting of PS1 in activate.
  * Add conda update --all.
  * Allow setting CONDARC=' ' to use no condarc.
  * Add conda clean --packages.
  * Don't include bin/conda, bin/activate, or bin/deactivate in conda
    package.


## 3.3.0 (2014-03-18)

  * allow new package specification, i.e. ==, >=, >, <=, <, != separated
    by ',' for example: >=2.3,<3.0
  * add ability to disable self update of conda, by setting
    "self_update: False" in .condarc
  * Try installing packages using the old way of just installing the maximum
    versions of things first. This provides a major speedup of solving the
    package specifications in the cases where this scheme works.
  * Don't include python=3.3 in the specs automatically for the Python 3
    version of conda.  This allows you to do "conda create -n env package" for
    a package that only has a Python 2 version without specifying
    "python=2". This change has no effect in Python 2.
  * Automatically put symlinks to conda, activate, and deactivate in each
    environment on Unix.
  * On Unix, activate and deactivate now remove the root environment from the
    PATH. This should prevent "bleed through" issues with commands not
    installed in the activated environment but that are installed in the root
    environment. If you have "setup.py develop" installed conda on Unix, you
    should run this command again, as the activate and deactivate scripts have
    changed.
  * Begin work to support Python 3.4.
  * Fix a bug in version comparison
  * Fix usage of sys.stdout and sys.stderr in environments like pythonw on
    Windows where they are nonstandard file descriptors.


## 3.2.1 (2014-03-12)

  * fix installing packages with irrational versions
  * fix installation in the api
  * use a logging handler to print the dots


## 3.2.0 (2014-03-11)

  * print dots to the screen for progress
  * move logic functions from resolve to logic module


## 3.2.0a1 (2014-03-07)

  * conda now uses pseudo-boolean constraints in the SAT solver. This allows
    it to search for all versions at once, rather than only the latest (issue
    #491).
  * Conda contains a brand new logic submodule for converting pseudo-boolean
    constraints into SAT clauses.


## 3.1.1 (2014-03-07)

  * check if directory exists, fixed issue #591


## 3.1.0 (2014-03-07)

  * local packages in cache are now added to the index, this may be disabled
    by using the --known option, which only makes conda use index metadata
    from the known remote channels
  * add --use-index-cache option to enable using cache of channel index files
  * fix ownership of files when installing as root on Linux
  * conda search: add '.' symbol for extracted (cached) packages


## 3.0.6 (2014-02-20)

  * fix 'conda update' taking build number into account


## 3.0.5 (2014-02-17)

  * allow packages from create_default_packages to be overridden from the
    command line
  * fixed typo install.py, issue #566
  * try to prevent accidentally installing into a non-root conda environment


## 3.0.4 (2014-02-14)

  * conda update: don't try to update packages that are already up-to-date


## 3.0.3 (2014-02-06)

  * improve the speed of clean --lock
  * some fixes to conda config
  * more tests added
  * choose the first solution rather than the last when there are more than
    one, since this is more likely to be the one you want.


## 3.0.2 (2014-02-03)

  * fix detection of prefix being writable


## 3.0.1 (2014-01-31)

  * bug: not having track_features in condarc now uses default again
  * improved test suite
  * remove numpy version being treated special in plan module
  * if the post-link.(bat|sh) fails, don't treat it as though it installed,
    i.e. it is not added to conda-meta
  * fix activate if CONDA_DEFAULT_ENV is invalid
  * fix conda config --get to work with list keys again
  * print the total download size
  * fix a bug that was preventing conda from working in Python 3
  * add ability to run pre-link script, issue #548


## 3.0.0 (2014-01-24)

  * removed build, convert, index, and skeleton commands, which are now
    part of the conda-build project: https://github.com/conda/conda-build
  * limited pip integration to `conda list`, that means
    `conda install` no longer calls `pip install` # !!!
  * add ability to call sub-commands named 'conda-x'
  * The -c flag to conda search is now shorthand for --channel, not
    --canonical (this is to be consistent with other conda commands)
  * allow changing location of .condarc file using the CONDARC environment
    variable
  * conda search now shows the channel that the package comes from
  * conda search has a new --platform flag for searching for packages in other
    platforms.
  * remove condarc warnings: issue #526#issuecomment-33195012


## 2.3.1 (2014-01-17)

  * add ability create info/no_softlink
  * add conda convert command to convert non-platform-dependent packages from
    one platform to another (experimental)
  * unify create, install, and update code. This adds many features to create
    and update that were previously only available to install. A backwards
    incompatible change is that conda create -f now means --force, not
    --file.


## 2.3.0 (2014-01-16)

  * automatically prepend http://conda.binstar.org/ (or the value of
    channel_alias in the .condarc file) to channels whenever the
    channel is not a URL or the word 'defaults or 'system'
  * recipes made with the skeleton pypi command will use setuptools instead of
    distribute
  * re-work the setuptools dependency and entry_point logic so that
    non console_script entry_points for packages with a dependency on
    setuptools will get correct build script with conda skeleton pypi
  * add -m, --mkdir option to conda install
  * add ability to disable soft-linking


## 2.2.8 (2014-01-06)

  * add check for chrpath (on Linux) before build is started, see issue #469
  * conda build: fixed ELF headers not being recognized on Python 3
  * fixed issues: #467, #476


## 2.2.7 (2014-01-02)

  * fixed bug in conda build related to lchmod not being available on all
    platforms


## 2.2.6 (2013-12-31)

  * fix test section for automatic recipe creation from pypi
    using --build-recipe
  * minor Py3k fixes for conda build on Linux
  * copy symlinks as symlinks, issue #437
  * fix explicit install (e.g. from output of `conda list -e`) in root env
  * add pyyaml to the list of packages which can not be removed from root
    environment
  * fixed minor issues: #365, #453


## 2.2.5 (2013-12-17)

  * conda build: move broken packages to conda-bld/broken
  * conda config: automatically add the 'defaults' channel
  * conda build: improve error handling for invalid recipe directory
  * add ability to set build string, issue #425
  * fix LD_RUN_PATH not being set on Linux under Python 3,
    see issue #427, thanks peter1000


## 2.2.4 (2013-12-10)

  * add support for execution with the -m switch (issue #398), i.e. you
    can execute conda also as: python -m conda
  * add a deactivate script for windows
  * conda build adds .pth-file when it encounters an egg (TODO)
  * add ability to preserve egg directory when building using
        build/preserve_egg_dir: True
  * allow track_features in ~/.condarc
  * Allow arbitrary source, issue #405
  * fixed minor issues: #393, #402, #409, #413


## 2.2.3 (2013-12-03)

  * add "foreign mode", i.e. disallow install of certain packages when
    using a "foreign" Python, such as the system Python
  * remove activate/deactivate from source tarball created by sdist.sh,
    in order to not overwrite activate script from virtualenvwrapper


## 2.2.2 (2013-11-27)

  * remove ARCH environment variable for being able to change architecture
  * add PKG_NAME, PKG_VERSION to environment when running build.sh,
    .<name>-post-link.sh and .<name>-pre-unlink.sh


## 2.2.1 (2013-11-15)

  * minor fixes related to make conda pip installable
  * generated conda meta-data missing 'files' key, fixed issue #357


## 2.2.0 (2013-11-14)

  * add conda init command, to allow installing conda via pip
  * fix prefix being replaced by placeholder after conda build on Unix
  * add 'use_pip' to condarc configuration file
  * fixed activate on Windows to set CONDA_DEFAULT_ENV
  * allow setting "always_yes: True" in condarc file, which implies always
    using the --yes option whenever asked to proceed


## 2.1.0 (2013-11-07)

  * fix rm_egg_dirs so that the .egg_info file can be a zip file
  * improve integration with pip
      * conda list now shows pip installed packages
      * conda install will try to install via "pip install" if no
        conda package is available (unless --no-pip is provided)
      * conda build has a new --build-recipe option which
        will create a recipe (stored in <root>/conda-recipes) from pypi
        then build a conda package (and install it)
      * pip list and pip install only happen if pip is installed
  * enhance the locking mechanism so that conda can call itself in the same
    process.


## 2.0.4 (2013-11-04)

  * ensure lowercase name when generating package info, fixed issue #329
  * on Windows, handle the .nonadmin files


## 2.0.3 (2013-10-28)

  * update bundle format
  * fix bug when displaying packages to be downloaded (thanks Crystal)


## 2.0.2 (2013-10-27)

  * add --index-cache option to clean command, see issue #321
  * use RPATH (instead of RUNPATH) when building packages on Linux


## 2.0.1 (2013-10-23)

  * add --no-prompt option to conda skeleton pypi
  * add create_default_packages to condarc (and --no-default-packages option
    to create command)


## 2.0.0 (2013-10-01)

  * added user/root mode and ability to soft-link across filesystems
  * added create --clone option for copying local environments
  * fixed behavior when installing into an environment which does not
    exist yet, i.e. an error occurs
  * fixed install --no-deps option
  * added --export option to list command
  * allow building of packages in "user mode"
  * regular environment locations now used for build and test
  * add ability to disallow specification names
  * add ability to read help messages from a file when install location is RO
  * restore backwards compatibility of share/clone for conda-api
  * add new conda bundle command and format
  * pass ARCH environment variable to build scripts
  * added progress bar to source download for conda build, issue #230
  * added ability to use url instead of local file to conda install --file
    and conda create --file options


## 1.9.1 (2013-09-06)

  * fix bug in new caching of repodata index


## 1.9.0 (2013-09-05)

  * add caching of repodata index
  * add activate command on Windows
  * add conda package --which option, closes issue 163
  * add ability to install file which contains multiple packages, issue 256
  * move conda share functionality to conda package --share
  * update documentation
  * improve error messages when external dependencies are unavailable
  * add implementation for issue 194: post-link or pre-unlink may append
    to a special file ${PREFIX}/.messages.txt for messages, which is display
    to the user's console after conda completes all actions
  * add conda search --outdated option, which lists only installed packages
    for which newer versions are available
  * fixed numerous Py3k issues, in particular with the build command


## 1.8.2 (2013-08-16)

  * add conda build --check option
  * add conda clean --lock option
  * fixed error in recipe causing conda traceback, issue 158
  * fixes conda build error in Python 3, issue 238
  * improve error message when test command fails, as well as issue 229
  * disable Python (and other packages which are used by conda itself)
    to be updated in root environment on Windows
  * simplified locking, in particular locking should never crash conda
    when files cannot be created due to permission problems


## 1.8.1 (2013-08-07)

  * fixed conda update for no arguments, issue 237
  * fix setting prefix before calling should_do_win_subprocess()
    part of issue 235
  * add basic subversion support when building
  * add --output option to conda build


## 1.8.0 (2013-07-31)

  * add Python 3 support (thanks almarklein)
  * add Mercurial support when building from source (thanks delicb)
  * allow Python (and other packages which are used by conda itself)
    to be updated in root environment on Windows
  * add conda config command
  * add conda clean command
  * removed the conda pip command
  * improve locking to be finer grained
  * made activate/deactivate work with zsh (thanks to mika-fischer)
  * allow conda build to take tarballs containing a recipe as arguments
  * add PKG_CONFIG_PATH to build environment variables
  * fix entry point scripts pointing to wrong python when building Python 3
    packages
  * allow source/sha1 in meta.yaml, issue 196
  * more informative message when there are unsatisfiable package
    specifications
  * ability to set the proxy urls in condarc
  * conda build asks to upload to binstar. This can also be configured by
    changing binstar_upload in condarc.
  * basic tab completion if the argcomplete package is installed and eval
    "$(register-python-argcomplete conda)" is added to the bash profile.


## 1.7.2 (2013-07-02)

  * fixed conda update when packages include a post-link step which was
    caused by subprocess being lazily imported, fixed by 0d0b860
  * improve error message when 'chrpath' or 'patch' is not installed and
    needed by build framework
  * fixed sharing/cloning being broken (issue 179)
  * add the string LOCKERROR to the conda lock error message


## 1.7.1 (2013-06-21)

  * fix "executable" not being found on Windows when ending with .bat when
    launching application
  * give a better error message from when a repository does not exist


## 1.7.0 (2013-06-20)

  * allow ${PREFIX} in app_entry
  * add binstar upload information after conda build finishes


## 1.7.0a2 (2013-06-20)

  * add global conda lock file for only allowing one instance of conda
    to run at the same time
  * add conda skeleton command to create recipes from PyPI
  * add ability to run post-link and pre-unlink script


## 1.7.0a1 (2013-06-13)

  * add ability to build conda packages from "recipes", using the conda build
    command, for some examples, see:
    https://github.com/ContinuumIO/conda-recipes
  * fixed bug in conda install --force
  * conda update command no longer uses anaconda as default package name
  * add proxy support
  * added application API to conda.api module
  * add -c/--channel and --override-channels flags (issue 121).
  * add default and system meta-channels, for use in .condarc and with -c
    (issue 122).
  * fixed ability to install ipython=0.13.0 (issue 130)


## 1.6.0 (2013-06-05)

  * update package command to reflect changes in repodata
  * fixed refactoring bugs in share/clone
  * warn when anaconda processes are running on install in Windows (should
    fix most permissions errors on Windows)


## 1.6.0rc2 (2013-05-31)

  * conda with no arguments now prints help text (issue 111)
  * don't allow removing conda from root environment
  * conda update python does no longer update to Python 3, also ensure that
    conda itself is always installed into the root environment (issue 110)


## 1.6.0rc1 (2013-05-30)

  * major internal refactoring
  * use new "depends" key in repodata
  * uses pycosat to solve constraints more efficiently
  * add hard-linking on Windows
  * fixed linking across filesystems (issue 103)
  * add conda remove --features option
  * added more tests, in particular for new dependency resolver
  * add internal DSL to perform install actions
  * add package size to download preview
  * add conda install --force and --no-deps options
  * fixed conda help command
  * add conda remove --all option for removing entire environment
  * fixed source activate on systems where sourcing a gives "bash" as $0
  * add information about installed versions to conda search command
  * removed known "locations"
  * add output about installed packages when update and install do nothing
  * changed default when prompted for y/n in CLI to yes


## 1.5.2 (2013-04-29)

  * fixed issue 59: bad error message when pkgs dir is not writable


## 1.5.1 (2013-04-19)

  * fixed issue 71 and (73 duplicate): not being able to install packages
    starting with conda (such as 'conda-api')
  * fixed issue 69 (not being able to update Python / NumPy)
  * fixed issue 76 (cannot install mkl on OSX)


## 1.5.0 (2013-03-22)

  * add conda share and clone commands
  * add (hidden) --output-json option to clone, share and info commands
    to support the conda-api package
  * add repo sub-directory type 'linux-armv6l'


## 1.4.6 (2013-03-12)

  * fixed channel selection (issue #56)


## 1.4.5 (2013-03-11)

  * fix issue #53 with install for meta packages
  * add -q/--quiet option to update command


## 1.4.4 (2013-03-09)

  * use numpy 1.7 as default on all platforms


## 1.4.3 (2013-03-09)

  * fixed bug in conda.builder.share.clone_bundle()


## 1.4.2 (2013-03-08)

  * feature selection fix for update
  * Windows: don't allow linking or unlinking python from the root
             environment because the file lock, see issue #42


## 1.4.1 (2013-03-07)

  * fix some feature selection bugs
  * never exit in activate and deactivate
  * improve help and error messages


## 1.4.0 (2013-03-05)

  * fixed conda pip NAME==VERSION
  * added conda info --license option
  * add source activate and deactivate commands
  * rename the old activate and deactivate to link and unlink
  * add ability for environments to track "features"
  * add ability to distinguish conda build packages from Anaconda
    packages by adding a "file_hash" meta-data field in info/index.json
  * add conda.builder.share module


## 1.3.5 (2013-02-05)

  * fixed detecting untracked files on Windows
  * removed backwards compatibility to conda 1.0 version


## 1.3.4 (2013-01-28)

  * fixed conda installing itself into environments (issue #10)
  * fixed non-existing channels being silently ignored (issue #12)
  * fixed trailing slash in ~/.condarc file cause crash (issue #13)
  * fixed conda list not working when ~/.condarc is missing (issue #14)
  * fixed conda install not working for Python 2.6 environment (issue #17)
  * added simple first cut implementation of remove command (issue #11)
  * pip, build commands: only package up new untracked files
  * allow a system-wide <sys.prefix>/.condarc (~/.condarc takes precedence)
  * only add pro channel is no condarc file exists (and license is valid)


## 1.3.3 (2013-01-23)

  * fix conda create not filtering channels correctly
  * remove (hidden) --test and --testgui options


## 1.3.2 (2013-01-23)

  * fix deactivation of packages with same build number
    note that conda upgrade did not suffer from this problem, as was using
    separate logic


## 1.3.1 (2013-01-22)

  * fix bug in conda update not installing new dependencies


## 1.3.0 (2013-01-22)

  * added conda package command
  * added conda index command
  * added -c, --canonical option to list and search commands
  * fixed conda --version on Windows
  * add this changelog


## 1.2.1 (2012-11-21)

  * remove ambiguity from conda update command


## 1.2.0 (2012-11-20)

  * "conda upgrade" now updates from AnacondaCE to Anaconda (removed
    upgrade2pro
  * add versioneer


## 1.1.0 (2012-11-13)

  * Many new features implemented by Bryan


## 1.0.0 (2012-09-06)

  * initial release
