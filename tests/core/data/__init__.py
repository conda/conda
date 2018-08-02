# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Example packages:

- https://github.com/frejanordsiek/hdf5storage/blob/0.1.15/setup.py
- https://github.com/dask/dask/blob/master/setup.py
- https://github.com/rdegges/django-twilio/blob/master/setup.py
- https://github.com/twilio/twilio-python/blob/master/setup.py
- https://github.com/tox-dev/tox/blob/master/setup.py
"""

import os

HERE = os.path.abspath(os.path.dirname(__file__))
PATH_TEST_ENV_1 = os.path.join(HERE, 'env1')
PATH_TEST_ENV_2 = os.path.join(HERE, 'env2')
#SITE_PACKAGES_PATH_1 = os.path.join(PATH_TEST_ENV_1, 'lib', 'python3.6', 'site-packages')
#SITE_PACKAGES_PATH_2 = os.path.join(PATH_TEST_ENV_2, 'lib', 'python2.7', 'site-packages')
#PATH_EGG_1 = os.path.join(HERE, 'eggdata', 'egg1')
#PATH_EGG_2 = os.path.join(HERE, 'eggdata', 'egg2')

METADATA_241_PATH = os.path.join(HERE, 'metadata', 'pep241', 'PKG-INFO')
METADATA_314_PATH = os.path.join(HERE, 'metadata', 'pep314', 'PKG-INFO')
METADATA_345_PATH = os.path.join(HERE, 'metadata', 'pep345', 'PKG-INFO')
METADATA_566_PATH = os.path.join(HERE, 'metadata', 'pep566', 'PKG-INFO')

METADATA_VERSION_PATHS = (METADATA_241_PATH, METADATA_314_PATH,
                          METADATA_345_PATH, METADATA_566_PATH)
