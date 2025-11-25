mkdir -p $PREFIX/etc/conda/activate.d
echo "echo 'setting TEST_VAR' && export TEST_VAR=1" > $PREFIX/etc/conda/activate.d/test.sh
chmod +x $PREFIX/etc/conda/activate.d/test.sh

mkdir -p $PREFIX/etc/conda/deactivate.d
echo "echo 'unsetting TEST_VAR' && unset TEST_VAR" > $PREFIX/etc/conda/deactivate.d/test.sh
chmod +x $PREFIX/etc/conda/deactivate.d/test.sh
