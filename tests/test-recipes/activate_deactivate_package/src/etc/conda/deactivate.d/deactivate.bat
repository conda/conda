@echo off&cls
setlocal EnableDelayedExpansion

set TEST=teststringfromactivate

set $line=%PATH%
set $line=%$line: =#%
set $line=%$line:;= %

for %%a in (%$line%) do echo %%a | find /i %TEST% || set $newpath=!$newpath!;%%a
set $newpath=!$newpath:#= !
set PATH=!$newpath:~1!
