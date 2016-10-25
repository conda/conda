# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# #                                                                     # #
# # APPVEYOR SCRIPT                                                     # #
# #                                                                     # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

###########################################################################
# HELPER FUNCTIONS                                                        #
function main_test() {
    Write-Output "MAIN TEST"

    $PYTHONHASHSEED=(python -c "import random as r; print(r.randint(0,4294967296))")
    Write-Output "${PYTHONHASHSEED}"

    # detect what shells are available to test with
    # refer to conda.util.shells for appropriate syntaxes
    $shells=""
    if (Get-Command cmd.exe -ErrorAction SilentlyContinue) {
        $shells="${shells} --shell=cmd.exe"
    }
    # if (Get-Command powershell.exe -ErrorAction SilentlyContinue) {
    #     $shells="${shells} --shell=powershell.exe"
    # }
    if (Get-Command C:\cygwin64\bin\bash.exe -ErrorAction SilentlyContinue) {
        $shells="${shells} --shell=bash.cygwin"
    }
    if (Get-Command C:\MinGW\msys\1.0\bin\bash.exe -ErrorAction SilentlyContinue) {
        $shells="${shells} --shell=bash.mingw"
    }
    if (Get-Command C:\msys64\usr\bin\bash.exe -ErrorAction SilentlyContinue) {
        $shells="${shells} --shell=bash.msys"
    }

    python -m pytest --cov-report xml ${shells} -m "not installed" tests

    # `develop` instead of `install` to avoid coverage issues of tracking two
    # separate "codes"
    python setup.py --version
    python setup.py develop
    Get-Command conda
    python -m conda info

    python -m pytest --cov-report xml --cov-append ${shells} -m "installed" tests

    Write-Output "END MAIN TEST"
}
# END HELPER FUNCTIONS                                                    #
###########################################################################

###########################################################################
# "MAIN FUNCTION"                                                         #
Write-Output "START SCRIPT"

# show basic environment details                                          #
Get-Command python
$_ENV=(Get-ChildItem env: | Select Name,Value)
$_ENV=$_ENV+(Get-Variable -Scope Global | Select Name,Value)
$_ENV | Sort Name

# remove duplicates from the $PATH                                        #
# Windows in general does poorly with long PATHs so just as a sanity      #
# check remove any duplicates                                             #
#                                                                         #
# replace ; with ? before calling batch program since powershell to batch #
# converts ; to linebreaks without explicit escaping \;                   #
$env:Path=(envvar_cleanup.bat ${env:PATH}.replace(";","?") --delim="?" -d).replace("?",";")

# perform the appropriate test setup                                      #
main_test

Write-Output "DONE SCRIPT"
# END "MAIN FUNCTION"                                                     #
###########################################################################
