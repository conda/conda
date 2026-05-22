### Bug fixes

* Fix channel notices display failing with `ImportError` when a decorated command replaces base `python` while conda is still running on the previous interpreter. Pre-import `conda.notices.views` before the command so post-command display does not load modules from rewritten `site-packages`. (#16126 via #16142)
