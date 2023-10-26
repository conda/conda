(deep_dive_activation)=
# `conda init` and `conda activate`

`conda` ships _virtual environments_ by design. When you install Anaconda or Miniconda, you obtain
a `base` environment that is essentially a regular environment with some extra checks. These checks
have to do with what the `conda` command really is and how it is installed in your system.

```{admonition} Base prefix vs target prefix
Originally, the base installation for `conda` was called the _root_ environment. Every other
environment lived under `envs/` in that root environment. The root environment was later renamed to
_base_, but the code still distinguishes between base and target using the old terminology:

* `context.root_prefix`: the path where the `base` conda installation is located.
* `context.target_prefix`: the environment `conda` is running a command on. Usually defaults to the
  activated environment, unless `-n` (name) or `-p` (prefix) is specified in the command line. Note
  that if you are operating on the `base` environment, the target prefix will have the same value
  as the root prefix.
```

When you type `conda` in your terminal, your shell will try to find either:
* a shell function named `conda`
* an executable file named `conda` in your `PATH` directories

If your `conda` installation has been properly initialized, it will find the shell function. If not,
it might find the `conda` executable if it _happens_ to be in `PATH`, but this is most often not the
case. That's why initialization is there to begin with!

## Conda initialization

Why is initialization needed at all to begin with? There are several reasons:

* Activation requires interacting with the shell context very closely
* It does not pollute `PATH` unnecessarily
* Improves performance in certain operations

The main idea behind initialization is to provide a `conda` shell function that allows the Python
code to interact with the shell context more intimately. It also allows a cleaner `PATH`
manipulation and snappier responses in some `conda` commands.

The `conda` shell function is mainly a [forwarder function][conda_shell_function]. It will
delegate most of the commands to the real `conda` executable driven by the Python library.
However, it will intercept two very specific subcommands:
* `conda activate`
* `conda deactivate`

This interception is needed because activation/deactivation requires exporting (or unsetting)
environment variables back to the shell session (and not just temporarily in the Python
process). This will be discussed in the next section.

So how is initialization performed? This is the job of the `conda init` subcommand, driven by
the `conda.cli.command.main_init` module, which depends direcly on the `conda.core.initialize` module. Let's
see how this is implemented.

`conda init` will initialize a shell permanently by writing some shell code in the relevant
startup scripts of your shell (e.g. `~/.bashrc`). This is done through different functions defined
in `conda.core.initialize`, namely:

* `init_sh_user`: initializes a Posix shell (like Bash) for the current user.
* `init_sh_system`: initializes a Posix shell (like Bash) globally, for all users.
* `init_fish_user`: initializes the Fish shell for the current user.
* `init_xonsh_user`: initializes the Xonsh shell for the current user.
* `init_cmd_exe_registry`: initializes Cmd.exe through the Windows Registry.
* `init_powershell_user`: initializes Powershell for the current user.
* `init_long_path`: configures Windows to support longer paths.


What each function does depends on the nature of each shell. In the case of Bash shells, the
underlying `Activator` subclass (more below) can generate the hook code dynamically. In other Posix
shells and Powershell, a script is sourced from its location in the `base` environment. With Cmd,
the changes are introduced through the Windows Registry. The end result is the same: they will
end up defining a `conda` shell function with the behavior described above.

## Conda activate

All `Activator` classes can be found under `conda.activate`. Their job is essentially to write
shell-native code programmatically. As of conda 4.11, these are the supported shells and their
corresponding activators

* `posix`, `ash`, `bash`, `dash`, `zsh`: all driven by `PosixActivator`.
* `csh`, `tcsh`: `CshActivator`.
* `xonsh`: `XonshActivator`.
* `cmd.exe`: `CmdExeActivator`.
* `fish`: `FishActivator`.
* `powershell`: `PowerShellActivator`.

You can add all these classes through the `conda shell.<key>` command, where `key` is
any of the names in the list above. These CLI interface offers several subcommands, connected
directly to methods of the same name:

* `activate`: writes the shell code to activate a given environment.
* `deactivate`: writes the shell code to deactivate a given environment.
* `hook`: writes the shell code to register the initialization code for the `conda` shell code.
* `commands`: writes the shell code needed for autocompletion engines.
* `reactivate`: writes the shell code for deactivation followed by activation.

To be clear, we are saying these functions only _write_ shell code. They do _not_ execute it! This
needs to be done by the shell itself! That's why we need a `conda` shell function, so these shell
strings can be `eval`'d or `source`'d in-session.

Let's see what happens when you run `conda shell.bash activate`:

```shell
$ conda shell.bash activate
export PATH='/Users/username/.local/anaconda/bin:/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/Users/username/.local/anaconda/condabin:/opt/homebrew/bin:/opt/homebrew/sbin'
unset CONDA_PREFIX_1
PS1='(base) '
export CONDA_PREFIX='/Users/username/.local/anaconda'
export CONDA_SHLVL='1'
export CONDA_DEFAULT_ENV='base'
export CONDA_PROMPT_MODIFIER='(base) '
export CONDA_EXE='/Users/username/.local/anaconda/bin/conda'
export _CE_M=''
export _CE_CONDA=''
export CONDA_PYTHON_EXE='/Users/username/.local/anaconda/bin/python'
```

See? It only wrote some shell code to stdout, but it wasn't executed. We would need to do this to
actually run it:

```shell
$ eval "$(conda shell.bash activate)"
```

And this is essentially what `conda activate` does: it calls the registered shell activator to
obtain the required shell code and then it `eval`s it. In some shells with no `eval` equivalent,
a temporary script is written and sourced or called. The final effect is the same.

Ok, but what is that shell code doing? Mainly setting your `PATH` correctly so the executables of
your `base` environment can be found (like `python`). It also sets some extra variables to keep
a reference to the path of the currently active environment, the shell prompt modifiers and
other information for `conda` internals.

This command can also generate the code for any other environment you want, not just `base`. Just
pass the name or path:

```shell
$ conda shell.bash activate mamba-poc
PS1='(mamba-poc) '
export PATH='/Users/username/.local/anaconda/envs/mamba-poc/bin:/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/Users/username/.local/anaconda/condabin:/opt/homebrew/bin:/opt/homebrew/sbin'
export CONDA_PREFIX='/Users/username/.local/anaconda/envs/mamba-poc'
export CONDA_SHLVL='2'
export CONDA_DEFAULT_ENV='mamba-poc'
export CONDA_PROMPT_MODIFIER='(mamba-poc) '
export CONDA_EXE='/Users/username/.local/anaconda/bin/conda'
export _CE_M=''
export _CE_CONDA=''
export CONDA_PYTHON_EXE='/Users/username/.local/anaconda/bin/python'
export CONDA_PREFIX_1='/Users/username/.local/anaconda'
```

Now the paths are different, as well as some numbers (e.g. `CONDA_SHLVL`). This is used by conda to
keep track of what was activated before, so when you deactivate the last one, you can get back to
the previous one seamlessly.

## Activation/deactivation scripts

The activation/deactivation code can also include calls to activation/deactivation scripts. If
present in the appropriate directories for your shell (e.g.
`CONDA_PREFIX/etc/conda/activate.d/`), they will be called before deactivation or after
activation, respectively. For example, compilers usually set up some environment variables to
help configure the default flags. This is what happens when you activate an environment that
contains Clang and Gfortran:

```shell
$ conda shell.bash activate compilers
PS1='(compilers) '
export PATH='/Users/username/.local/anaconda/envs/compilers/bin:/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/Users/username/.local/anaconda/condabin:/opt/homebrew/bin:/opt/homebrew/sbin'
export CONDA_PREFIX='/Users/username/.local/anaconda/envs/compilers'
export CONDA_SHLVL='2'
export CONDA_DEFAULT_ENV='compilers'
export CONDA_PROMPT_MODIFIER='(compilers) '
export CONDA_EXE='/Users/username/.local/anaconda/bin/conda'
export _CE_M=''
export _CE_CONDA=''
export CONDA_PYTHON_EXE='/Users/username/.local/anaconda/bin/python'
export CONDA_PREFIX_1='/Users/username/.local/anaconda'
. "/Users/username/.local/anaconda/envs/compilers/etc/conda/activate.d/activate-gfortran_osx-arm64.sh"
. "/Users/username/.local/anaconda/envs/compilers/etc/conda/activate.d/activate_clang_osx-arm64.sh"
. "/Users/username/.local/anaconda/envs/compilers/etc/conda/activate.d/activate_clangxx_osx-arm64.sh"
```

Those three lines are sourcing the relevant scripts. Similarly, for deactivation, notice how the
deactivation scripts are executed first this time:

```shell
$ conda shell.bash deactivate
export PATH='/Users/username/.local/anaconda/bin:/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/Users/username/.local/anaconda/condabin:/opt/homebrew/bin:/opt/homebrew/sbin'
. "/Users/username/.local/anaconda/envs/compilers/etc/conda/deactivate.d/deactivate_clangxx_osx-arm64.sh"
. "/Users/username/.local/anaconda/envs/compilers/etc/conda/deactivate.d/deactivate_clang_osx-arm64.sh"
. "/Users/username/.local/anaconda/envs/compilers/etc/conda/deactivate.d/deactivate-gfortran_osx-arm64.sh"
unset CONDA_PREFIX_1
PS1='(base) '
export CONDA_PREFIX='/Users/username/.local/anaconda'
export CONDA_SHLVL='1'
export CONDA_DEFAULT_ENV='base'
export CONDA_PROMPT_MODIFIER='(base) '
export CONDA_EXE='/Users/username/.local/anaconda/bin/conda'
export _CE_M=''
export _CE_CONDA=''
export CONDA_PYTHON_EXE='/Users/username/.local/anaconda/bin/python'
```

<!-- Links -->

[conda_shell_function]: https://github.com/conda/conda/blob/4.11.0/conda/shell/etc/profile.d/conda.sh#L62-L76
