#!/bin/bash -e

TST_DIR=$HOME/ctest
RT_BIN=$TST_DIR/anaconda/bin

rm -rf $TST_DIR
mkdir $TST_DIR
cd $TST_DIR
wget http://filer/miniconda/Miniconda-1.9.1-Linux-x86_64.sh
bash Miniconda-1.9.1-Linux-x86_64.sh -b -p anaconda
$RT_BIN/conda install --yes distribute

cd $HOME/conda
$RT_BIN/python setup.py develop
$RT_BIN/conda info
