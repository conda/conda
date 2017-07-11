::    These lines are for Windows only. Requires being in
::    Intel Compiler prompt before running conda-build.
::    Intel Compiler prompt for VS 2010 worked OK on Python 2.7, VS 2015 tried
::    to use Win 10 SDK and did not work.  Latest Intel tools
::    (16.0 Update 1) do not explicitly support 2008 any more.

if "%ARCH%" == "64" (
 set "PATH=C:\Program Files (x86)\IntelSWTools\compilers_and_libraries\windows\bin\intel64;%PATH%"
) else (
 set "PATH=C:\Program Files (x86)\IntelSWTools\compilers_and_libraries\windows\bin\ia32;%PATH%"
)

python setup.py config_fc --f77flags="/fpp" install
