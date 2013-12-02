#!/bin/bash

# Use this bash script to generate the conda source tarball which gets
# uploaded to PyPI.

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
rm -f conda/_version.py*
cat <<EOF >conda/__init__.py
__version__ = '$VERSION'
EOF
rm versioneer.py
touch versioneer.py
replace 'version=versioneer.get_version(),' "version='$VERSION'," setup.py
replace 'cmdclass=versioneer.get_cmdclass(),' '' setup.py
replace 'add_activate = True' 'add_activate = False' setup.py
sdist
git reset --hard
