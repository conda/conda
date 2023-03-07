Debugging Conda's Unit Test with VSCode
=======================================

This is one way to debug conda's unit tests using
[VSCode](https://code.visualstudio.com/) on OSX.

1. In a conda checkout, run `. dev/start -p 3.10` to enter a Python 3.10 (or the
   version you want to test) development environment.
2. Open VSCode from this terminal `code`.
    > If `code` is not available, press `⌘-P`, `Shell` to find the `Install
    > 'code' command in PATH` action.
3. Ensure you have installed the `Python` extension.
4. Open settings (the gear icon in the lower left corner). Go to `Open Settings
   (JSON)` (the paper icon with an arrow on it, above the settings editor).
5. Conda's tests really want to run under the under-develoment version of conda,
   and may refuse to run at all otherwise. Add or edit `"python.condaPath":
   "(full path to conda in development environment)",`.
    > On my system, this can be found with `conda info`: `base
    > environment :
    > /Users/dholth/prog/conda/devenv/Darwin/arm64/envs/devenv-3.10-c`, plus
    > `/bin/conda`, so the full setting is `"python.condaPath":
    > "/Users/dholth/prog/conda/devenv/Darwin/arm64/envs/devenv-3.10-c/bin/conda",`
6. Press the Erlenmeyer flask "Testing" icon in the VSCode toolbar. Click on
   `Refresh Tests`. You should see a long list of tests.
7. Press 'Run Test', or 'Debug Test' for the test(s) you would like to examine.
8. Remember to comment out `// "python.condaPath":` with `//` when you are not
   debugging conda; normal `VSCode` usage should run the normal `conda`.

See also [VSCode's documentation for its Python
debugger](https://code.visualstudio.com/docs/python/debugging).
