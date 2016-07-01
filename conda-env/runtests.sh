#!/bin/bash
# Install nose, nose-progressive, and watchdog
watchmedo shell-command -R -p "*.py" \
  -c "nosetests --with-progressive"
