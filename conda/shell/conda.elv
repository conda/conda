# Conda integration for Elvish

fn conda [@args]{
  if (eq $args []) {
    -conda-exe
  } else {
    var cmd = $args[0]
    cmd-args = $args[1:]
    if (has-value [activate deactivate] $cmd) {
      eval (-conda-exe shell.elvish $cmd $@cmd-args | slurp)
    } elif (has-value [install update upgrade remove uninstall] $cmd) {
      -conda-exe $cmd $@cmd-args
      eval (-conda-exe shell.elvish reactivate)
    } else {
      -conda-exe $cmd $@cmd-args
    }
  }
}

# Add the conda function to the interactive namespace
edit:add-var conda~ $conda~
