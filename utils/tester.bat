@REM # tester

@REM entering a LOCAL scope, this effectively means that we do not
@REM need to explicitly unset anything but we do need to explicitly
@REM declare variables that need to be preserved
@SETLOCAL EnableDelayedExpansion

@SET "URL=https://repo.continuum.io/miniconda/Miniconda2-latest-Windows-x86_64.exe"
@SET "DST=C:\Users\appveyor\miniconda_installer.exe"

@ECHO "GOT URL & FILENAME"
@CD
@ECHO "!URL!    !DST!"

@CALL .\utils\appveyor-downloader.ps1 "!URL!" "!DST!"
