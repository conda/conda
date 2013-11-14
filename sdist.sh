#!/bin/bash

VERSION=$(git describe)
echo "VERSION: '$VERSION'"

cat <<EOF >conda/__init__.py
__version__ = '$VERSION'
EOF

replace 'version=versioneer.get_version(),' "version='$VERSION'," setup.py

sdist

git reset --hard
