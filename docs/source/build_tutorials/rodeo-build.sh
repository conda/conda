#!/bin/bash

$PYTHON setup.py install

if [ `uname` == Darwin ]
then
    cp $RECIPE_DIR/rodeo_mac.command $PREFIX/bin
fi

# Add more build steps here, if they are necessary.

# See
# http://docs.continuum.io/conda/build.html
# for a list of environment variables that are set during the build process.
