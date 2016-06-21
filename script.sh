conda uninstall numpy
conda uninstall xarray
cd $HOME/anaconda2/pkgs
rm -rf xarray-0.7.2-py27_0
rm xarray-0.7.2-py27_0.*
rm numpy-1.11.0-py27_1.*
rm -rf numpy-1.11.0-py27_1
cd $CONDA_HOME
conda install xarray
