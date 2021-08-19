# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
r"""
Example packages used in this data testing:
- https://github.com/cherrypy/cherrypy.git
- https://github.com/dask/dask.git
- https://github.com/rdegges/django-twilio.git
- https://github.com/frejanordsiek/hdf5storage.git
- https://github.com/jaraco/keyring.git
- https://github.com/scrapy/scrapy.git
- https://github.com/tox-dev/tox.git
- https://github.com/twilio/twilio-python.git


conda create -y -p ./tenv python=2 numpy h5py nomkl lxml
conda activate ./tenv
git clone https://github.com/frejanordsiek/hdf5storage.git && pushd hdf5storage && git checkout 0.1.15 && pip install . --no-binary :all: && popd && rm -rf hdf5storage
git clone https://github.com/cherrypy/cherrypy.git && pushd cherrypy && git checkout v17.2.0 && pip install . --no-binary :all: && popd && rm -rf cherrypy
git clone https://github.com/dask/dask.git && pushd dask && git checkout 0.18.2 && pip install . --no-binary :all: && popd && rm -rf dask
git clone https://github.com/rdegges/django-twilio.git && pushd django-twilio && git checkout 0.9.2 && pip install . --no-binary :all: && popd && rm -rf django-twilio
git clone https://github.com/jaraco/keyring.git && pushd keyring && git checkout 13.2.1 && pip install . --no-binary :all: && popd && rm -rf keyring
git clone https://github.com/scrapy/scrapy.git && pushd scrapy && git checkout 1.5.1 && pip install . --no-binary :all: && popd && rm -rf scrapy
git clone https://github.com/tox-dev/tox.git && pushd tox && git checkout 3.2.1 && pip install . --no-binary :all: && popd && rm -rf tox
git clone https://github.com/twilio/twilio-python.git && pushd twilio-python && git checkout 6.16.1 && pip install . --no-binary :all: && popd && rm -rf twilio-python
conda deactivate



conda create -y -p ./tenv python=2 numpy h5py nomkl lxml pip=8
./tenv/bin/pip install --no-binary :all: twilio==6.16.1
./tenv/bin/pip install --no-binary :all: hdf5storage==0.1.15
./tenv/bin/pip install --no-binary :all: cherrypy==17.2.0
./tenv/bin/pip install --no-binary :all: dask==0.18.2
./tenv/bin/pip install --no-binary :all: django-twilio==0.9.2
./tenv/bin/pip install --no-binary :all: keyring==13.2.1
./tenv/bin/pip install --no-binary :all: scrapy==1.5.1
./tenv/bin/pip install --no-binary :all: tox==3.2.1
./tenv/bin/pip install --no-binary :all: backports.weakref
./tenv/bin/pip install --no-binary :all: backports.pdb
./tenv/bin/pip install --no-binary :all: backports.shutil_which

mkdir -p ./py27-osx-no-binary/lib/python2.7
mv ./tenv/lib/python2.7/site-packages ./py27-osx-no-binary/lib/python2.7/
mv ./tenv/conda-meta ./py27-osx-no-binary/
rm -rf ./tenv
find ./py27-osx-no-binary \( -name \*.py -o -name \*.py[cod] -o -name __pycache__ \) -delete
find ./py27-osx-no-binary \( -name \*.so -o -name \*.h -o -name \*.c -o -name \*.mo -o -name \*.po -o -name \*.cfg \) -delete
find ./py27-osx-no-binary \( -name \*.pxd -o -name \*.dat -o -name \*.pem -o -name \*.rng -o -name \*.xsl \) -delete
find ./py27-osx-no-binary -type d \( -name django -o -name zoneinfo -o -name twisted -o -name cherrypy -o -name scrapy -o -name numpy \) | xargs rm -rf
find ./py27-osx-no-binary -type d \( -name setuptools -o -name lxml -o -name virtualenv_support -o -name pip -o -name enum \) | xargs rm -rf
# find ./py27-osx-no-binary \( -name SOURCES.txt \) -delete
find ./py27-osx-no-binary -type d | gtac | xargs rmdir || true




conda create -y -p ./tenv python=3.6 numpy h5py nomkl lxml
./tenv/bin/pip install twilio==6.16.1
./tenv/bin/pip install hdf5storage==0.1.15
./tenv/bin/pip install cherrypy==17.2.0
./tenv/bin/pip install dask==0.18.2
./tenv/bin/pip install django-twilio==0.9.2
./tenv/bin/pip install keyring==13.2.1
./tenv/bin/pip install scrapy==1.5.1
./tenv/bin/pip install tox==3.2.1

mkdir -p ./py36-osx-whl/lib/python3.6
mv ./tenv/lib/python3.6/site-packages ./py36-osx-whl/lib/python3.6/
mv ./tenv/conda-meta ./py36-osx-whl/
rm -rf ./tenv
find ./py36-osx-whl \( -name \*.py -o -name \*.py[cod] -o -name __pycache__ \) -delete
find ./py36-osx-whl \( -name \*.so -o -name \*.h -o -name \*.c -o -name \*.mo -o -name \*.po -o -name \*.cfg \) -delete
find ./py36-osx-whl \( -name \*.pxd -o -name \*.dat -o -name \*.pem -o -name \*.rng -o -name \*.xsl \) -delete
find ./py36-osx-whl -type d \( -name django -o -name zoneinfo -o -name twisted -o -name cherrypy -o -name scrapy -o -name numpy \) | xargs rm -rf
find ./py36-osx-whl -type d \( -name setuptools -o -name lxml -o -name virtualenv_support -o -name pip -o -name enum \) | xargs rm -rf
find ./py36-osx-whl -type d | gtac | xargs rmdir || true




"""

import os

HERE = os.path.abspath(os.path.dirname(__file__))

# Test environment installed using either `pip install <pth-to-wheel>` or
# `python setup.py install`
PATH_TEST_ENV_1 = os.path.join(HERE, 'envpy27osx')
PATH_TEST_ENV_2 = os.path.join(HERE, 'envpy37osx_whl')
PATH_TEST_ENV_3 = os.path.join(HERE, 'envpy37win')
PATH_TEST_ENV_4 = os.path.join(HERE, 'envpy27win_whl')

METADATA_241_PATH = os.path.join(HERE, 'pep241', 'PKG-INFO')
METADATA_314_PATH = os.path.join(HERE, 'pep314', 'PKG-INFO')
METADATA_345_PATH = os.path.join(HERE, 'pep345', 'PKG-INFO')
METADATA_566_PATH = os.path.join(HERE, 'pep566', 'PKG-INFO')

METADATA_VERSION_PATHS = (METADATA_241_PATH, METADATA_314_PATH,
                          METADATA_345_PATH, METADATA_566_PATH)
