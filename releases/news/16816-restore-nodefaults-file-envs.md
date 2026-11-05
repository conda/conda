### Bug fixes

* Restore `nodefaults` handling for file-based environments so configured channels are no longer appended and `nodefaults` is not requested as a channel. `nodefaults` in the configured channel list or `-c` is stripped before solving. (#16816 via #16947)
