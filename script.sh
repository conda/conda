conda uninstall numpy
conda uninstall xarray
cd /Users/zhangtian/anaconda2/pkgs
rm -rf xarray-0.7.2-py35_0
rm xarray-0.7.2-py35_0.*
rm numpy-1.11.0-py35_0.*
rm -rf numpy-1.11.0-py35_0
cd $CONDA_HOME
conda install xarray
