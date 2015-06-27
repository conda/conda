#!/bin/bash
echo "Running tests on any file change"
echo
echo "Hit Ctrl+C to stop"
echo
watchmedo shell-command \
  -c "py.test -m 'not slow' $@" \
  -p "*.py" -R
