@ECHO ON
pushd %TEMP%

set CONDA=C:\Miniconda
mklink /J \conda_bin %CONDA%
mklink /J \conda_src %GITHUB_WORKSPACE%

cd \conda_src
CALL \conda_bin\scripts\activate.bat
CALL conda create -n conda-test-env -y python=%PYTHON% pywin32 --file=tests\requirements.txt
CALL conda activate conda-test-env
CALL conda install -yq pip conda-build conda-verify
CALL conda update openssl ca-certificates certifi
python -m conda init cmd.exe --dev
