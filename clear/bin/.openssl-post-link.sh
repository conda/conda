#!/bin/bash

# break hard link
cp $PREFIX/lib/libcrypto.1.0.0.dylib $PREFIX/lib/libcrypto.1.0.0.dylib-tmp
mv $PREFIX/lib/libcrypto.1.0.0.dylib-tmp $PREFIX/lib/libcrypto.1.0.0.dylib

$PREFIX/bin/.openssl-libcrypto-fix $PREFIX
