unlink $PREFIX/bin/conda
CONDA_DEFAULT_ENV='' $PYTHON setup.py install
CONDA_DEFAULT_ENV='' python setup.py --version > __conda_version__.txt

# link to exec folder as a more contained proxy.  Idea is that people can add exec folder to PATH
#    instead of bin, and have only activate & conda on PATH - no trampling other stuff.
mkdir -p $PREFIX/exec
ln -s $PREFIX/bin/activate $PREFIX/exec/activate
ln -s $PREFIX/bin/conda $PREFIX/exec/conda

mkdir -p $PREFIX/etc/fish/conf.d/
cp $SRC_DIR/shell/conda.fish $PREFIX/etc/fish/conf.d/
