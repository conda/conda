#!/bin/bash

# Remove the symlinked versions of activate/deactivate
rm $PREFIX/bin/activate
rm $PREFIX/bin/deactivate

$PYTHON setup.py install
