# necessary because conda symlinks
unlink $PREFIX/bin/conda || true
unlink $PREFIX/bin/activate || true
unlink $PREFIX/bin/deactivate || true

$PYTHON conda.recipe/setup.py install

mkdir -p $PREFIX/etc/fish/conf.d/
cp $SRC_DIR/shell/conda.fish $PREFIX/etc/fish/conf.d/

mkdir -p $PREFIX/etc/profile.d
echo "_CONDA_EXE=\"$PREFIX/bin/conda\"" > $PREFIX/etc/profile.d/conda.sh
cat $SRC_DIR/shell/conda.sh >> $PREFIX/etc/profile.d/conda.sh

mkdir -p $PREFIX/bin

cat $SRC_DIR/shell/activate >> $PREFIX/bin/activate


cp $SRC_DIR/shell/conda.sh $PREFIX/etc/profile.d/

mkdir -p $PREFIX/etc/conda/activate.d
ln -s $PREFIX/etc/profile.d/conda.sh $PREFIX/etc/conda/activate.d/
