# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
#
# INSTALL
#
#     Run 'conda init fish' and restart your shell.
#

if not set -q CONDA_SHLVL
    set -gx CONDA_SHLVL 0
    set -g _CONDA_ROOT (dirname (dirname $CONDA_EXE))
    set -gx PATH $_CONDA_ROOT/condabin $PATH
end

if not set -q _CONDA_PS1_PASSTHROUGH
    and set -q PS1
    # Some Linux distros drop PS1, but let other variables pass
    # We sneak PS1 through this proxy variable for some entry points
    # We only define it if it wasn't defined already! Otherwise the
    # PS1 prompt keeps growing every time you source bashrc et al.
    set -gx _CONDA_PS1_PASSTHROUGH "$PS1"
fi

function __conda_add_prompt
    if set -q CONDA_PROMPT_MODIFIER
        set_color -o green
        echo -n $CONDA_PROMPT_MODIFIER
        set_color normal
    end
end

if functions -q fish_prompt
    if not functions -q __fish_prompt_orig
        functions -c fish_prompt __fish_prompt_orig
    end
    functions -e fish_prompt
else
    function __fish_prompt_orig
    end
end

function return_last_status
    return $argv
end

function fish_prompt
    set -l last_status $status
    if set -q CONDA_LEFT_PROMPT
        __conda_add_prompt
    end
    return_last_status $last_status
    __fish_prompt_orig
end

if functions -q fish_right_prompt
    if not functions -q __fish_right_prompt_orig
        functions -c fish_right_prompt __fish_right_prompt_orig
    end
    functions -e fish_right_prompt
else
    function __fish_right_prompt_orig
    end
end

function fish_right_prompt
    if not set -q CONDA_LEFT_PROMPT
        __conda_add_prompt
    end
    __fish_right_prompt_orig
end


function conda --inherit-variable CONDA_PYTHON_EXE --inherit-variable _CE_I --inherit-variable _CE_M --inherit-variable _CE_CONDA
    if [ (count $argv) -lt 1 ]
        $CONDA_PYTHON_EXE $_CE_I $_CE_M $_CE_CONDA
    else
        set -l cmd $argv[1]
        set -e argv[1]
        switch $cmd
            case activate deactivate
                eval ($CONDA_PYTHON_EXE $_CE_I $_CE_M $_CE_CONDA shell.fish $cmd $argv)
            case install update upgrade remove uninstall
                $CONDA_PYTHON_EXE $_CE_I $_CE_M $_CE_CONDA $cmd $argv
                and eval ($CONDA_PYTHON_EXE $_CE_I $_CE_M $_CE_CONDA shell.fish reactivate)
            case '*'
                $CONDA_PYTHON_EXE $_CE_I $_CE_M $_CE_CONDA $cmd $argv
        end
    end
end




# Autocompletions below


# Faster but less tested (?)
function __fish_conda_commands
    string replace -r '.*_([a-z]+)\.py$' '$1' $_CONDA_ROOT/lib/python*/site-packages/conda/cli/main_*.py
    for f in $_CONDA_ROOT/bin/conda-*
        if test -x "$f" -a ! -d "$f"
            string replace -r '^.*/conda-' '' "$f"
        end
    end
    echo activate
    echo deactivate
end

function __fish_conda_env_commands
    string replace -r '.*_([a-z]+)\.py$' '$1' $_CONDA_ROOT/lib/python*/site-packages/conda_env/cli/main_*.py
end

function __fish_conda_envs
    conda config --json --show envs_dirs | python -c "import json, os, sys; from os.path import isdir, join; print('\n'.join(d for ed in json.load(sys.stdin)['envs_dirs'] if isdir(ed) for d in os.listdir(ed) if isdir(join(ed, d))))"
end

function __fish_conda_packages
    conda list | awk 'NR > 3 {print $1}'
end

function __fish_conda_needs_command
    set cmd (commandline -opc)
    if [ (count $cmd) -eq 1 -a $cmd[1] = conda ]
        return 0
    end
    return 1
end

function __fish_conda_using_command
    set cmd (commandline -opc)
    if [ (count $cmd) -gt 1 ]
        if [ $argv[1] = $cmd[2] ]
            return 0
        end
    end
    return 1
end

# Conda commands
complete -f -c conda -n __fish_conda_needs_command -a '(__fish_conda_commands)'
complete -f -c conda -n '__fish_conda_using_command env' -a '(__fish_conda_env_commands)'

# Commands that need environment as parameter
complete -f -c conda -n '__fish_conda_using_command activate' -a '(__fish_conda_envs)'

# Commands that need package as parameter
complete -f -c conda -n '__fish_conda_using_command remove' -a '(__fish_conda_packages)'
complete -f -c conda -n '__fish_conda_using_command uninstall' -a '(__fish_conda_packages)'
complete -f -c conda -n '__fish_conda_using_command upgrade' -a '(__fish_conda_packages)'
complete -f -c conda -n '__fish_conda_using_command update' -a '(__fish_conda_packages)'
