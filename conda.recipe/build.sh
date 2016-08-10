# necessary because conda symlinks
unlink $PREFIX/bin/conda
unlink $PREFIX/bin/activate
unlink $PREFIX/bin/deactivate

export CONDA_DEFAULT_ENV=''
$PYTHON setup.py install

mkdir -p $PREFIX/etc/fish/conf.d/
cp $SRC_DIR/shell/conda.fish $PREFIX/etc/fish/conf.d/
