# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals
from logging import getLogger
import os
import sys
from zipfile import ZipFile

from conda.common.path import expand
from conda.gateways.subprocess import subprocess_call
from conda.gateways.connection.download import download

log = getLogger(__name__)



download("https://download.sysinternals.com/files/Handle.zip", "handle.zip", "07ad4eed22435653c239245cdef6996a")
with ZipFile("handle.zip") as fh:
    fh.extractall()

print("handle.zip extracted", file=sys.stderr)
print(os.listdir('.'), file=sys.stderr)

result = subprocess_call(expand('handle -accepteula'))
# print(result.stdout, file=sys.stderr)
# print(result.stderr, file=sys.stderr)

