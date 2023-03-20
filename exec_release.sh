#!/bin/bash
#conda create -n rever conda-forge::rever
conda init
conda activate rever

#git clone https://github.com/fyu17/conda.git
#cd conda
git checkout -b release-23.3.0
rever --activities authors 1.0