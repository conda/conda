#!/usr/bin/env awk -f

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# #                                                                     # #
# # WHICHSHELL.AWK                                                      # #
# # detect the shell used based on a collection of values               # #
# # this is the SECOND filtering of what shell the user is running      # #
# #                                                                     # #
# # this works in conjunction with the other whichshell*                # #
# #                                                                     # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

BEGIN {}
{
    #######################################################################
    # DETECT CLAUSE/MODE                                                  #
    clause_failure = "[WHICHSHELL]: ERROR: Bad clause."
    clause = substr($NF,1,1)
    debug = substr($NF,2,1)
    if (clause == "e") {
        # error clause
        clause = 1
    } else if (clause == "b") {
        # bourne shell clause
        clause = 2
    } else if (clause == "c") {
        # c-shell clause
        clause = 3
    } else {
        # bad clause
        print clause_failure > "/dev/stderr"
        exit(2)
    }
    # debug clause
    if (debug == "d") {
        debug = 0 == 0
    } else {
        debug = 0 == 1
    }
    # END DETECT CLAUSE/MODE                                              #
    #######################################################################

    #######################################################################
    # PARSE PARAMETERS                                                    #
    # expect to recieve in this order:                                    #
    #  1) the process command, generally speaking: ps -o "comm=" -p $$    #
    #  2) the current sytem, generally speaking: lsb_release -si/uname -s #
    #  3) $SHLVL                                                          #
    #  4) $0                                                              #
    #  5) script's name                                                   #
    #  6) clause/mode (detected above)                                    #
    scriptname = $(NF-1)
    shell_failure = "["toupper(scriptname)"]: ERROR: Only supports "      \
                    "sourcing from tcsh/csh and bash/zsh/dash/posh. (1)"
    num = split($0,a," ")
    if (num != 6) {
        if (clause == 1)
            print shell_failure > "/dev/stderr"
        exit(clause != 1)
    }
    shell           = "."a[1]
    sys             = a[2]
    shlvl           = a[3]
    szero           = a[4]
    scriptname      = a[5]
    scriptname_re   = ".*"a[5]".*"
    smatch          = match(szero,scriptname_re) == 0
    # END PARSE PARAMETERS                                                #
    #######################################################################

    #######################################################################
    # DEBUG STATEMENTS                                                    #
    # enabling these are useful to see what kind of scenario to add to    #
    # the below shell matching                                            #
    if (debug) {
        print("shell: "shell)
        print("sys: "sys)
        print("shlvl: "shlvl)
        print("szero: "szero)
        print("scriptname_re: "scriptname_re)
        print("smatch: "smatch)
    }
    # END DEBUG STATEMENTS                                                #
    #######################################################################

    #######################################################################
    # MATCH SHELL                                                         #
    shell_failure = "["toupper(scriptname)"]: ERROR: Only supports "      \
                    "sourcing from tcsh/csh and bash/zsh/dash/posh. (2)"
    if (smatch                                                  &&
        ((shell == ".bash")                                     ||
         (shell == ".-bash")                                    ||
         (shell == "./bin/bash")                                ||
         (shell == ".-bin/bash"))) {
        exit(clause != 2)
    }
    if ((shell == ".zsh")                                       ||
        (shell == ".-zsh")                                      ||
        (shell == "./bin/zsh")                                  ||
        (shell == ".-bin/zsh")) {
        exit(clause != 2)
    }
    if (smatch                                                  &&
        ((shell == ".dash")                                     ||
         (shell == ".-dash")                                    ||
         (shell == "./bin/dash")                                ||
         (shell == ".-/bin/dash")                               ||
         (shell == ".sh" && sys == "Ubuntu"))) {
        exit(clause != 2)
    }
    if ((shell == ".posh")                                      ||
        (shell == ".-posh")                                     ||
        (shell == "./bin/posh")                                 ||
        (shell == ".-/bin/posh")) {
        exit(clause != 2)
    }
    # the default shell is generally difficult/impossible to accurately
    # detect, further users don't work in the default shell so support for
    # this is debateable
    if (smatch                                                  &&
        ((shell == ".sh" && sys != "Ubuntu")                    ||
         (shell == ".-sh" && sys == "Darwin" && shlvl == "1")   ||
         (shell == ".-sh" && sys == "Linux")                    ||
         (shell == "./bin/sh")                                  ||
         (shell == ".-bin/sh"))) {
        exit(clause != 2)
    }
    if (smatch                                                  &&
        ((shell == ".csh")                                      ||
         (shell == ".-csh" && sys == "Darwin" && shlvl == "1")  ||
         (shell == ".-sh"  && sys == "Darwin" && shlvl != "1")  ||
         (shell == ".-sh"  && sys == "Ubuntu" && shlvl == "1")  ||
         (shell == ".-csh" && sys == "Linux")                   ||
         (shell == "./bin/csh")                                 ||
         (shell == ".-bin/csh"))) {
        exit(clause != 3)
    }
    if (smatch                                                  &&
        ((shell == ".tcsh")                                     ||
         (shell == ".-tcsh" && sys == "Darwin" && shlvl == "1") ||
         (shell == ".-csh"  && sys == "Darwin" && shlvl != "1") ||
         (shell == ".-csh"  && sys == "Ubuntu" && shlvl != "1") ||
         (shell == ".-tcsh" && sys == "Linux")                  ||
         (shell == "./bin/tcsh")                                ||
         (shell == ".-bin/tcsh"))) {
        exit(clause != 3)
    }
    if (clause == 1)
        print shell_failure > "/dev/stderr"
    exit(clause != 1)
    # END MATCH SHELL                                                     #
    #######################################################################
}
END {}
