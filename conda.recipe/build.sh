# necessary because conda symlinks
if [ -L $PREFIX/bin/conda ]; then
    unlink $PREFIX/bin/conda
    unlink $PREFIX/bin/activate
    unlink $PREFIX/bin/deactivate
fi

$PYTHON conda.recipe/setup.py install

#cat <<- EOF > $PREFIX/bin/conda
##!$PYTHON -O
#if __name__ == '__main__':
#   import sys
#   import conda.cli.main
#   sys.exit(conda.cli.main.main())
#EOF
#

# fish setup
mkdir -p $PREFIX/etc/fish/conf.d/
cp $SRC_DIR/shell/conda.fish $PREFIX/etc/fish/conf.d/
