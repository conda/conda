# Bundled Windows launchers

These files remain for compatibility while conda uses the
`conda-launchers` package for Windows entry points.

## cli-64.exe

Released conda clients, including 26.7.2, copy this file when creating
Windows entry points. During a self-upgrade, the running process still
uses that code after conda's package files have been replaced. Keeping
this file in the new package lets those transactions finish.

This behavior was introduced in conda 26.3.0 by
[#15678](https://github.com/conda/conda/pull/15678). Earlier versions copied
`Scripts/conda.exe` instead.

## cli-32.exe

This file is the fallback when the installed or selected
`conda-launchers` package does not provide a 32-bit launcher.

## Removal

Neither file has a scheduled removal date. Before removing either,
we need a safe upgrade path for released clients that still read it.
Users can skip releases, so retaining it for one extra release cycle
does not solve this.

Removing `cli-32.exe` also requires the supported `conda-launchers`
packages to provide a 32-bit launcher.
