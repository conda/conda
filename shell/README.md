# Activate and Deactivate

The `activate` and `deactivate` scripts are the core programs that effectively enable and disable conda virtual environments.

The majority of these files are expected to be installed into the Anaconda bin directory and effectively available on the user's `$PATH`.

There are three code families for activate and deactivate:

1. POSIX Compliant Unix Shells
2. Non-POSIX Compliant Unix Shell
3. Windows Batch

## POSIX Compliant Unix Shells

This family contains the bulk of the logic and code. Within POSIX unix shells we support two families; bourne shell and c-shell. Both the activate and deactivate branches described below consult the `whichshell.awk`, `whichshell_args.bash`, and `whichshell_ps.bash` scripts.

For testing and debugging use `test_whichshell` to see how the `whichshell*` codes respond in certain unix shell configurations (e.g. `csh` vs. `bash -l` vs. `dash` etc.). The various conditionals that are detected there can be used to modify the logic in `whichshell.awk`.

Users will interact directly with the `activate` and `deactivate` points.

If for whatever reason the `activate` and `deactivate` scripts are unable to properly detect the user's shell you can always call the appropriate `activate` and `deactivate`:

```
# Bourne Shell Family
. activate.sh

# C Shell Family
source "`which activate.csh`"
```

### Activate Branch
```
           - activate.sh
          /
activate -
          \
           - activate.csh
```

### Deactivate Branch
```
             - deactivate.sh
            /
deactivate -
            \
             - deactivate.csh
```

## Non-POSIX Compliant Unix Shell

This is the family of shells that cannot be incorporated into the POSIX Compliant Unix Shell logic due to missing key structures and utilities. These shells are generally supported ad hoc.

These will generally require additional work to configure initially in your environment but once configured is expected to function much like the POSIX Compliant Unix Shell family.

### FISH

## Windows Batch

This provides unique support for the Windows Cmd Prompt.