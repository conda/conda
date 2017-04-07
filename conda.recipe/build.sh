# necessary because conda symlinks
unlink $PREFIX/bin/conda
unlink $PREFIX/bin/activate
unlink $PREFIX/bin/deactivate

$PYTHON conda.recipe/setup.py install

# fish setup
mkdir -p $PREFIX/etc/fish/conf.d/
cp $SRC_DIR/shell/conda.fish $PREFIX/etc/fish/conf.d/
