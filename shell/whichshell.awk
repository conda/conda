#!/usr/bin/env awk -f
BEGIN {}
{
    ######################################################################
    # detect the clause/mode
    ######################################################################
    clause_failure = "[WHICHSHELL]: ERROR: Bad clause."
    clause = substr($NF,1,1)
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

    ######################################################################
    # parse parameters
    ######################################################################
    # expect to recieve in this order:
    #  1) the process command, this boils down to being: ps -o "comm=" -p $$
    #  2) the current sytem, this boild down to being: lsb_release -si/uname -s
    #  3) $SHLVL
    #  4) script's name
    #  5) which clause
    scriptname = $(NF-1)
    parse_failure = "["toupper(scriptname)"]: ERROR: Parsing failure.\n["toupper(scriptname)"]: ERROR: This most likely means you executed the script instead of sourcing it."
    num = split($0,a," ")
    if (num != 5) {
        if (clause == 1) {
            print parse_failure > "/dev/stderr"
        }
        exit(clause != 1)
    }
    shell       = "."a[1]
    sys         = a[2]
    shlvl       = a[3]
    scriptname  = a[4]

    ######################################################################
    # debug statements
    ######################################################################
    # enabling these are useful to see what kind of scenario to add to
    # the below shell matching
    # print("shell: "shell)
    # print("sys: "sys)
    # print("shlvl: "shlvl)
    # print("scriptname: "scriptname)

    ######################################################################
    # match shell
    ######################################################################
    shell_failure = "["toupper(scriptname)"]: ERROR: Only supports sourcing from tcsh/csh and bash/zsh/dash/posh."
    if ((shell == ".bash")                                      ||
        (shell == ".-bash")                                     ||
        (shell == "./bin/bash")                                 ||
        (shell == ".-bin/bash")) {
        exit(clause != 2)
    }
    # when sourcing zsh $0 looks the same as executing
    # zsh being sourced vs executed is detected via the number of parameters parsed above
    if ((shell == ".zsh")                                        ||
        (shell == ".-zsh")                                       ||
        (shell == "./bin/zsh")                                   ||
        (shell == ".-bin/zsh")) {
        exit(clause != 2)
    }
    if ((shell == ".dash")                                      ||
        (shell == ".-dash")                                     ||
        (shell == "./bin/dash")                                 ||
        (shell == ".-/bin/dash")                                ||
        (shell == ".sh" && sys == "Ubuntu")) {
        exit(clause != 2)
    }
    if ((shell == ".posh")                                      ||
        (shell == ".-posh")                                     ||
        (shell == "./bin/posh")                                 ||
        (shell == ".-/bin/posh")) {
        exit(clause != 2)
    }
    # special corner cases tests are done here (and for
    # csh and tcsh) to address the oddities of Ubuntu vs.
    # Mac vs. other Linux distibutions
    if ((shell == ".sh" && sys != "Ubuntu")                     ||
        (shell == ".-sh" && sys == "Darwin" && shlvl == "1")    ||
        (shell == ".-sh" && sys == "Linux")                     ||
        (shell == "./bin/sh")                                   ||
        (shell == ".-bin/sh")) {
        exit(clause != 2)
    }
    if ((shell == ".csh")                                       ||
        (shell == ".-csh" && sys == "Darwin" && shlvl == "1")   ||
        (shell == ".-sh"  && sys == "Darwin" && shlvl != "1")   ||
        (shell == ".-sh"  && sys == "Ubuntu" && shlvl == "1")   ||
        (shell == ".-csh" && sys == "Linux")                    ||
        (shell == "./bin/csh")                                  ||
        (shell == ".-bin/csh")) {
        exit(clause != 3)
    }
    if ((shell == ".tcsh")                                      ||
        (shell == ".-tcsh" && sys == "Darwin" && shlvl == "1")  ||
        (shell == ".-csh"  && sys == "Darwin" && shlvl != "1")  ||
        (shell == ".-csh"  && sys == "Ubuntu" && shlvl != "1")  ||
        (shell == ".-tcsh" && sys == "Linux")                   ||
        (shell == "./bin/tcsh")                                 ||
        (shell == ".-bin/tcsh")) {
        exit(clause != 3)
    }
    print shell_failure > "/dev/stderr"
    exit(clause != 1)
}
END {}
