# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# #                                                                     # #
# # APPVEYOR INSTALL                                                    # #
# #                                                                     # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

###########################################################################
# HELPER FUNCTIONS                                                        #
function test_extras() {
    echo "TEST EXTRAS"

    # install/upgrade unittest dependencies
    python -m pip install -U mock pytest pytest-cov pytest-timeout radon
    python -m pip install -U responses anaconda-client nbformat

    echo "END TEST EXTRAS"
}


# this install shares similarities to Travis CI installation's            #
# python_install and miniconda_install functions                          #
function miniconda_install () {
    Write-Output "MINICONDA INSTALL"

    # get, install, and verify miniconda
    if (! Test-Path "${HOME}\miniconda") {
        if (! Test-Path "${HOME}\miniconda_installer.exe") {
            # build download url
            $filename = "x86_64"
            if ($PYTHON_ARCH -eq "32") {
                $filename = "x86"
            }
            if ($PYTHON_VERSION -like "2.*") {
                $filename = "Miniconda2-latest-Windows-" + $filename + ".exe"
            } ElseIf ($PYTHON_VERSION -like "3.*") {
                $filename = "Miniconda3-latest-Windows-" + $filename + ".exe"
            } Else {
                $filename = "Miniconda-latest-Windows-" + $filename + ".exe"
            }

            # try download up to 3 times in case of network transient errors
            $webclient = (New-Object System.Net.WebClient)
            $retry_attempts = 3
            for ($i=0; $i -lt $retry_attempts; $i++) {
                try {
                    $webclient.DownloadFile("${MINICONDA_URL}\${filename}", "${HOME}\miniconda_installer.exe")
                    break
                } catch [Exception] {
                    if ($i + 1 -eq $retry_attempts) {
                        throw $_.Exception
                    } else {
                        Start-Sleep 1
                    }
                }
            }
        }

        # run install
        Start-Process -FilePath "${HOME}\miniconda_installer.exe" -ArgumentList "/S /D=${HOME}\miniconda" -Wait -Passthru
    }
    # check for success
    if (! Test-Path "${HOME}\miniconda") {
        Write-Output "MINICONDA INSTALL FAILED"
        Get-Content -Path "${HOME}\miniconda.log"
        Exit 1
    }

    # update PATH
    $ANACONDA_PATH="${PYTHON};${PYTHON}/Scripts;${PYTHON}/Library/bin;${PYTHON}/Library/usr/bin;${PYTHON}/Library/mingw-64/bin"
    $env:PATH="${ANACONDA_PATH};${PATH}"
    Get-Command conda
    # this causes issues with Miniconda3 4.0.5
    # python -m conda info
    # this does not cause issues with Miniconda3 4.0.5
    conda info

    # install and verify pip
    conda install -y -q pip
    Get-Command pip

    # verify python
    Get-Command python

    # disable automatic updates
    conda config --set auto_update_conda false
    # conda config --set always_yes yes
    # conda update conda

    # install/upgrade basic dependencies
    python -m pip install -U psutil ruamel.yaml pycosat pycrypto
    if ($PYTHON_VERSION -like "2.*") {
        python -m pip install -U enum34 futures
    }

    Write-Output "END MINICONDA INSTALL"
}
# END HELPER FUNCTIONS                                                    #
###########################################################################

# - conda install -q python=%PYTHON_VERSION%
# - conda install -q requests
# - conda install -q pyflakes
# - conda install -q git menuinst
# - pip install flake8
# - python --version
# - python -c "import struct; print(struct.calcsize('P') * 8)"
# - python setup.py install
# - Write-Output "CMD.EXE VERSION"
# - cmd.exe /c "ver"
# - Write-Output "BASH.EXE VERSION"
# - bash.exe --version

###########################################################################
# "MAIN FUNCTION"                                                         #
Write-Output "START INSTALLING"

# set globals
$MINICONDA_URL = "http://repo.continuum.io/miniconda/"

# If there is a newer build queued for the same PR, cancel this one.
# The AppVeyor 'rollout builds' option is supposed to serve the same
# purpose but it is problematic because it tends to cancel builds pushed
# directly to master instead of just PR builds (or the converse).
# credits: JuliaLang developers.
$_NEWEST="https://ci.appveyor.com/api/projects/${env:APPVEYOR_ACCOUNT_NAME}/${env:APPVEYOR_PROJECT_SLUG}/history?recordsNumber=50"
$_NEWEST=((Invoke-RestMethod $_NEWEST).builds | Where-Object pullRequestId)
$_NEWEST=($_NEWEST -eq $env:APPVEYOR_PULL_REQUEST_NUMBER)[0].buildNumber
if ($env:APPVEYOR_PULL_REQUEST_NUMBER -and $env:APPVEYOR_BUILD_NUMBER -ne $_NEWEST) {
    throw "There are newer queued builds for this pull request, failing early."
}

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

# remove any stray CONDARC                                                #
if (Test-Path "${HOME}/.condarc") {
    Remove-Item "${HOME}/.condarc"
}

# perform the appropriate install                                         #
miniconda_install
test_extras

Write-Output "DONE INSTALLING"
# END "MAIN FUNCTION"                                                     #
###########################################################################
