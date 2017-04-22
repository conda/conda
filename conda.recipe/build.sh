# necessary because conda symlinks
unlink $PREFIX/bin/conda
unlink $PREFIX/bin/activate
unlink $PREFIX/bin/deactivate

$PYTHON conda.recipe/setup.py install
$PYTHON conda.recipe/setup.py --version > __conda_version__.txt

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
