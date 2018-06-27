echo $PKG_VERSION > conda/.version
python setup.py install --single-version-externally-managed --record record.txt
rm -rf "$SP_DIR/conda/shell/*.exe"
python -m conda init --install
