echo $PKG_VERSION > conda/.version
python setup.py install --single-version-externally-managed --record record.txt
rm -rf "$SP_DIR/conda/shell/*.exe"
conda init --install

# TODO: these are only meant to be temporary
rm -f "$PREFIX/bin/activate"
echo "#!/bin/sh" > "$PREFIX/bin/activate"
echo "_CONDA_ROOT=\"$PREFIX\"" >> "$PREFIX/bin/activate"
cat "$SP_DIR/conda/shell/bin/activate" >> "$PREFIX/bin/activate"

rm -f "$PREFIX/bin/deactivate"
echo "#!/bin/sh" > "$PREFIX/bin/deactivate"
echo "_CONDA_ROOT=\"$PREFIX\"" >> "$PREFIX/bin/deactivate"
cat "$SP_DIR/conda/shell/bin/deactivate" >> "$PREFIX/bin/deactivate"
