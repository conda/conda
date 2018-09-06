echo $PKG_VERSION > conda/.version
$PYTHON setup.py install --single-version-externally-managed --record record.txt
rm -rf "$SP_DIR/conda/shell/*.exe"
$PYTHON -m conda init --install
