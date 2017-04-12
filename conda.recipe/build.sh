# necessary because conda symlinks
unlink $PREFIX/bin/conda
unlink $PREFIX/bin/activate
unlink $PREFIX/bin/deactivate

$PYTHON conda.recipe/setup.py install
$PYTHON conda.recipe/setup.py --version > __conda_version__.txt

mkdir -p $PREFIX/etc/fish/conf.d/
cp $SRC_DIR/shell/conda.fish $PREFIX/etc/fish/conf.d/

mkdir -p $PREFIX/etc/profile.d
cp $SRC_DIR/shell/conda.sh $PREFIX/etc/profile.d/
