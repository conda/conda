#!/bin/bash

VERSION=$(git describe --dirty)
echo "VERSION: '$VERSION'"

echo $VERSION | grep dirty
if (( $? )); then
    echo "CLEAN"
else
    echo "DIRTY"
    echo "Error: You must commit your changes before creating a tarball." 
    exit 1
fi

rm -rf build dist docs/build conda.egg-info

cat <<EOF >conda/__init__.py
__version__ = '$VERSION'
EOF

replace 'version=versioneer.get_version(),' "version='$VERSION'," setup.py
sdist
git reset --hard
