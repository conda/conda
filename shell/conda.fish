#
# Conda environment activate / deactivate functions for fish shell v2.2.0+.
#
# Ivan Smirnov (C) 2015
#
# Envvars and autocompletions by @jaimergp, 2016

#
# INSTALL
#
#     Source this file from the fish shell to enable activate / deactivate functions.
#     In order to automatically load these functions on fish startup, append
#
#         source (conda info --root)/etc/fish/conf.d/conda.fish
#
#     to the end of your ~/.config/config.fish file.
#
# USAGE
#
#     To activate an environment (via name or path), you can use one of the following:
#
#         activate ENV
#         conda activate ENV
#
#     To deactivate an environment, use one of:
#
#         deactivate
#         conda deactivate
#
#     To make the env name appear on the left side, set an environment variable:
#
#         set -gx CONDA_LEFT_PROMPT 1
#
#     To go back to making the env name appear on the right, erase that variable:
#
#         set -e CONDA_LEFT_PROMPT


# Require version fish v2.0+ to be able to use array slices, `else if`
# and $status for command substitutions
if [ (echo (fish -v ^&1) | sed 's/^.*version \([0-9]\)\..*$/\1/') -lt 2 ]
    echo 'Incompatible fish shell version; please upgrade to v2.0 or higher.'
    exit 1
end


function __conda_delete_function
    functions -e $argv
    if functions -q $argv
        functions -e $argv
    end
end


function __conda_restore_prompt
    if functions -q __fish_prompt_orig
        __conda_delete_function fish_prompt
        functions -c __fish_prompt_orig fish_prompt
        functions -e __fish_prompt_orig
    end

    if functions -q __fish_right_prompt_orig
        __conda_delete_function fish_right_prompt
        functions -c __fish_right_prompt_orig fish_right_prompt
        functions -e __fish_right_prompt_orig
    end
end


function __conda_backup_prompt
    functions -e __fish_prompt_orig
    if functions -q fish_prompt
        functions -c fish_prompt __fish_prompt_orig
        functions -e fish_prompt
    else
        function __fish_prompt_orig
        end
    end

    functions -e __fish_right_prompt_orig
    if functions -q fish_right_prompt
        functions -c fish_right_prompt __fish_right_prompt_orig
        functions -e fish_right_prompt
    else
        function __fish_right_prompt_orig
        end
    end
end

function __conda_echo_env
  set_color normal
  echo -n '('
  set_color -o green
  echo -n $CONDA_DEFAULT_ENV
  set_color normal
  echo -n ') '
end


# Inject environment name into fish_right_prompt / fish_prompt
function __conda_update_prompt
      switch $argv[1]
          case activate
              __conda_restore_prompt
              __conda_backup_prompt
              function fish_prompt
                  if set -q CONDA_LEFT_PROMPT
                      __conda_echo_env
                  end
                  __fish_prompt_orig
              end
              function fish_right_prompt
                  if not set -q CONDA_LEFT_PROMPT
                      __conda_echo_env
                  end
                  __fish_right_prompt_orig
              end
          case deactivate
              __conda_restore_prompt
      end
end


# Calls activate / deactivate functions if the first argument is activate or
# deactivate; otherwise, calls conda-<cmd> and passes the arguments through
function conda
    if [ (count $argv) -lt 1 ]
        command conda
    else
        if [ (count $argv) -gt 1 ]
            set ARGS $argv[2..-1]
        else
            set -e ARGS
        end
        switch $argv[1]
            case activate deactivate
                eval $argv
            case '*'
                command conda $argv
        end
    end
end


# Equivalent to bash version of conda deactivate script
function deactivate --description 'Deactivate the current conda environment.'
    if set -q CONDA_DEFAULT_ENV  # don't deactivate the root environment
          # execute all *.fish scripts in deactivate.d
          set -l deactivate_scripts $CONDA_PREFIX/etc/conda/deactivate.d/*.fish
          for script in $deactivate_scripts
              source $script
          end
          set -gx PATH $CONDA_BACKUP_PATH
          set -e CONDA_DEFAULT_ENV
          set -e CONDA_BACKUP_PATH
          set -e CONDA_PREFIX
          __conda_update_prompt deactivate
    end
    # return 0
end


# Equivalent to bash version of conda activate script
function activate --description 'Activate a conda environment.'
    if [ (count $argv) -lt 1 ]
        echo 'You need to specify a conda environment.'
        return 1
    end

    # deactivate an environment first if it's set
    if set -q CONDA_DEFAULT_ENV
        conda '..checkenv' 'fish' $argv[1]
        if [ $status = 0 ]
            deactivate
            __conda_update_prompt deactivate
        else
            return 1
        end
    end

    # try to activate the environment
    set -l NEW_PATH (conda '..activate' 'fish' $argv[1])
    if [ $status = 0 ]
        set -gx CONDA_BACKUP_PATH $PATH
        set -gx PATH $NEW_PATH $PATH
        if [ (echo $argv[1] | grep '/') ]
          pushd (dirname $argv[1])
          set -gx CONDA_DEFAULT_ENV (pwd)/(basename $argv[1])
          popd
        else
          set -gx CONDA_DEFAULT_ENV $argv[1]
        end
        # Always store the full prefix path as CONDA_PREFIX
        set -gx CONDA_PREFIX (echo $PATH[1] | sed 's|/bin$||g')

        # execute all *.fish scripts in activate.d
        set -l activate_scripts $CONDA_PREFIX/etc/conda/activate.d/*.fish
        for script in $activate_scripts
            source $script
        end

        if [ (conda '..changeps1') = "1" ]
          __conda_update_prompt activate
        end
    else
        return $status
    end
end

# Autocompletions below

# Original implementations, but slow
# function __fish_conda_commands
#   command conda help | awk '/^    \S/ {print $1}'
# end
# function __fish_conda_envs
#   command conda env list | awk 'NR > 2 {print $1}'
# end


# Faster but less tested (?)
function __fish_conda_commands
  command echo -e "activate\ndeactivate" ;and ls --color=none (conda info --root)/bin/conda-* | sed -r 's/^.*conda-([a-z]+)/\1/'
end

function __fish_conda_envs
  command echo root ;and ls -1 --color=none (conda info --root)/envs/
end

function __fish_conda_packages
  command conda list | awk 'NR > 2 {print $1}'
end

function __fish_conda_needs_command
  set cmd (commandline -opc)
  if [ (count $cmd) -eq 1 -a $cmd[1] = 'conda' ]
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
complete -f -c conda -n '__fish_conda_needs_command' -a '(__fish_conda_commands)'

# Commands that need environment as parameter
complete -f -c conda -n '__fish_conda_using_command activate' -a '(__fish_conda_envs)'

# Commands that need package as parameter
complete -f -c conda -n '__fish_conda_using_command remove' -a '(__fish_conda_packages)'
complete -f -c conda -n '__fish_conda_using_command upgrade' -a '(__fish_conda_packages)'
complete -f -c conda -n '__fish_conda_using_command update' -a '(__fish_conda_packages)'
