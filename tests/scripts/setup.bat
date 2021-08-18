@ECHO ON
pushd %TEMP%

set CONDA=C:\Miniconda
mklink /J \conda_bin %CONDA%
mklink /J \conda_src %GITHUB_WORKSPACE%

cd \conda_src
CALL \conda_bin\scripts\activate.bat
CALL conda create -n ci_base -y python=%PYTHON% pycosat conda requests ruamel_yaml pytest pytest-cov pytest-timeout mock responses urllib3 pexpect pywin32 anaconda-client conda-package-handling conda-forge::pytest-split %SCANDIR%
CALL conda activate ci_base
CALL conda install -yq pip conda-build conda-verify
CALL conda update openssl ca-certificates certifi
python -m conda init cmd.exe --dev
