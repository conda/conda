# Activate and Deactivate

The `activate` and `deactivate` scripts are the core programs that effectively enable and disable conda virtual environments.

The majority of these files are expected to be installed into the Anaconda bin directory (on Unix) and Anaconda Script directory (on Windows) and effectively available on the user's `$PATH`.

There are three code families for activate and deactivate:

1. POSIX Compliant Unix Shells
2. Non-POSIX Compliant Unix Shell
3. Windows Batch

All of the codes have been designed to reflect the greatest similarity in their design logic to simplify longterm maintenance. In other words if you changed some logic in say the Windows Batch code, similar changes should be made to the POSIX and Non-POSIX Compliant Unix Shell codes.

## POSIX Compliant Unix Shells

This family contains the bulk of the logic and code. Within POSIX unix shells we support two sub-families; bourne shell and c-shell. Both the activate and deactivate branches described below consult the `whichshell.awk`, `whichshell_args.bash`, and `whichshell_ps.bash` scripts.

For testing and debugging use `test_whichshell` to see how the `whichshell*` codes respond in certain unix shell configurations (e.g. `csh` vs. `bash -l` vs. `dash` etc.). The various conditionals that are detected there can be used to modify the logic in `whichshell.awk`.

Users interact directly with the `activate` and `deactivate` programs:

```
# Dot-Sourcing (Bourne Shell Family)
. activate
. deactivate

# Source-Keyword (C Shell Family)
source "`which activate`"
source "`which deactivate`"
```

However, if for whatever reason the `activate` and `deactivate` scripts are unable to properly detect the user's shell you can always call the appropriate `activate.*` and `deactivate.*` directly:

```
# Bourne Shell Family
. activate.sh
. deactivate.sh

# C Shell Family
source "`which activate.csh`"
source "`which deactivate.csh`"
```

The purpose of the `activate` and `deactivate` scripts, which act as entry points, is to detect what shell the user is running and whether they are correctly sourcing the script. The danger of calling `*.sh` and `*.csh` directly is that there are no built in checks that will determine whether the user has correctly sourced said script. Having properly detected the shell and determined that the script is being sourced, `activate` and `deactivate` will source the appropriate script for the given shell (`*.sh` or `*.csh`).

## Non-POSIX Compliant Unix Shell

This is the family of shells that cannot be incorporated into the POSIX Compliant Unix Shell logic due to missing key structures and utilities. These shells are generally supported ad hoc.

These will generally require additional work to configure initially in your environment but once configured is expected to function much like the POSIX Compliant Unix Shell family.

### FISH
TODO: `conda.fish`

## Windows Batch

This provides unique support for the Windows Cmd Prompt.