# Conda integration for Elvish

# The following environment variables are recognized to control the position and
# style of the conda prompt indicator:
# - E:CONDA_LEFT_PROMPT - if the variable exists (regardless of value), the
#   indicator is added to the left prompt. By default, it is added to the right
#   prompt.
# - E:CONDA_PROMPT_MODIFIER_STYLE - by default "green" is used. Multiple
#   attributes can be separated by spaces, e.g. "red bold". See
#   https://elv.sh/ref/builtin.html#styled for documentation of style
#   transformers.

# General setup - initialize CONDA_SHLVL and add condabin to the PATH
if (not (has-env CONDA_SHLVL)) {
  E:CONDA_SHLVL = 0
  var -conda-root = (dirname (dirname $E:CONDA_EXE))
  set paths = [$-conda-root/condabin $@paths]
}

# Entry point for conda command
fn conda [@args]{
  if (eq $args []) {
    -conda-exe
  } else {
    var cmd = $args[0]
    var cmd-args = $args[1..]
    if (has-value [activate deactivate reactivate] $cmd) {
      eval (-conda-exe shell.elvish $cmd $@cmd-args | slurp)
    } elif (has-value [install update upgrade remove uninstall config] $cmd) {
      -conda-exe $cmd $@cmd-args
      conda reactivate
    } else {
      -conda-exe $cmd $@cmd-args
    }
  }
}

# Add the conda function to the interactive namespace
edit:add-var conda~ $conda~

# Prompt indicator

fn -conda-add-indicator {
  if (!=s $E:CONDA_PROMPT_MODIFIER '') {
    style = green
    if (has-env CONDA_PROMPT_MODIFIER_STYLE) {
      style = $E:CONDA_PROMPT_MODIFIER_STYLE
    }
    styled $E:CONDA_PROMPT_MODIFIER $style
  }
}

var -conda-original-prompt-fn~ = $edit:prompt
var -conda-original-rprompt-fn~ = $edit:rprompt

edit:prompt = {
  if (has-env CONDA_LEFT_PROMPT) {
    -conda-add-indicator
  }
  -conda-original-prompt-fn
}

edit:rprompt = {
  if (not (has-env CONDA_LEFT_PROMPT)) {
    -conda-add-indicator
  }
  -conda-original-rprompt-fn
}
