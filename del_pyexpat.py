# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals
from logging import getLogger
import sys
log = getLogger(__name__)


from conda.gateways.logging import initialize_logging
initialize_logging()

from conda.gateways.disk.delete import *
try:
    fn = sys.argv[1] if len(sys.argv) > 1 else 'pyexpat.pyd'
    rm_rf_wait('c:\\conda-root\\envs\\env-1\\DLLs\\%s' % fn)
except Exception as e:
    import pdb; pdb.set_trace()
    assert 1
