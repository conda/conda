# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Example packages used in this data testing:
- https://github.com/cherrypy/cherrypy.git
- https://github.com/dask/dask.git
- https://github.com/rdegges/django-twilio.git
- https://github.com/frejanordsiek/hdf5storage.git
- https://github.com/jaraco/keyring.git
- https://github.com/scrapy/scrapy.git
- https://github.com/tox-dev/tox.git
- https://github.com/twilio/twilio-python.git
"""

import os

HERE = os.path.abspath(os.path.dirname(__file__))

# Test environment installed using either `pip install <pth-to-wheel>` or
# `python setup.py install`
PATH_TEST_ENV_1 = os.path.join(HERE, 'envpy27osx')
PATH_TEST_ENV_2 = os.path.join(HERE, 'envpy37osx_whl')
PATH_TEST_ENV_3 = os.path.join(HERE, 'envpy27win')
PATH_TEST_ENV_4 = os.path.join(HERE, 'envpy37win_whl')

METADATA_241_PATH = os.path.join(HERE, 'metadata', 'pep241', 'PKG-INFO')
METADATA_314_PATH = os.path.join(HERE, 'metadata', 'pep314', 'PKG-INFO')
METADATA_345_PATH = os.path.join(HERE, 'metadata', 'pep345', 'PKG-INFO')
METADATA_566_PATH = os.path.join(HERE, 'metadata', 'pep566', 'PKG-INFO')

METADATA_VERSION_PATHS = (METADATA_241_PATH, METADATA_314_PATH,
                          METADATA_345_PATH, METADATA_566_PATH)
