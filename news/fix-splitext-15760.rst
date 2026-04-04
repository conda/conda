Fix AttributeError when renaming files to trash on Windows (#15760).

When conda attempts to rename a file that is in use (e.g., during conda update --all on Windows),
it would crash with AttributeError: 'str' object has no attribute 'splitext'.
This has been fixed by using os.path.splitext() instead.