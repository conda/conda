# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

set correct_conda_alias="source ${_CONDA_ROOT}/etc/profile.d/conda.csh"

if (!("`alias conda`" == "$correct_conda_alias")) then
    setenv CONDA_SHLVL 0
    alias conda $correct_conda_alias
else
    switch ( "${1}" )
        case "activate":
            set ask_conda="`(setenv prompt '${prompt}' ; '${_CONDA_EXE}' shell.csh activate '${2}' ${argv[3-]})`"
            set conda_tmp_status=$status
            if( $conda_tmp_status != 0 ) exit ${conda_tmp_status}
            eval "${ask_conda}"
            rehash
            breaksw
        case "deactivate":
            set ask_conda="`(setenv prompt '${prompt}' ; '${_CONDA_EXE}' shell.csh deactivate '${2}' ${argv[3-]})`"
            set conda_tmp_status=$status
            if( $conda_tmp_status != 0 ) exit ${conda_tmp_status}
            eval "${ask_conda}"
            rehash
            breaksw
        case "install" | "update" | "upgrade" | "remove" | "uninstall":
            $_CONDA_EXE $argv[1-]
            set ask_conda="`(setenv prompt '${prompt}' ; '${_CONDA_EXE}' shell.csh reactivate)`"
            set conda_tmp_status=$status
            if( $conda_tmp_status != 0 ) exit ${conda_tmp_status}
            eval "${ask_conda}"
            rehash
            breaksw
        default:
            $_CONDA_EXE $argv[1-]
            breaksw
    endsw
endif
