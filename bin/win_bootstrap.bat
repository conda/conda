:: Small script to allow conda to udpate Python in the root environment.
:: conda cannot do this because it itself runs in Python, and Windows will not
:: allow writing to a dll that is open.

:: This script should remain as small as possible. Only those things that
:: conda itself cannot do should be here. The rest should be done by
:: conda.

:: The way this works is that when conda comes to an action that it cannot
:: perform (such as linking Python in the root environment), it serializes the
:: rest of the actions it intends to perform, serializes the action that it
:: cannot perfom, calls this script, and exits. This script then reads the
:: serialized form of the action conda could not perform and then calls conda
:: to continue where it left off.

:: Implementation wise, the conda searlization is just a text dump of the
:: remainder of the plan in %PREFIX%\remainder.plan. The plan is already in a
:: nice text format (see tests/simple.plan for an example), so little work
:: needs to be done serialization-wise. The action serialization is just a
:: list of pairs of files that should be linked, written to
:: %PREFIX%\bootstrap_list (note, we can assume that we have write permissions
:: to %PREFIX% because otherwise we wouldn't be able to install in the root
:: environment anyway (this issue only comes up when installing into the root
:: environment)). conda calls this script and exits. This script reads the
:: action file, links the files listed therein, and calls conda ..continue
:: (and then exits). conda ..continue causes conda to pick up where it left
:: off from the remainder.plan file.

:: Notes:
::
:: - `mklink /H` creates a hardlink on Windows NT 6.0 and later (i.e., Windows
:: Vista or later)
:: - On older systems, like Windows XP, `fsutil.exe hardlink create` creates
:: hard links.

:: @echo off

FOR /F "tokens=1,2 delims=," %%i ("%1") DO @echo %%i %%j
