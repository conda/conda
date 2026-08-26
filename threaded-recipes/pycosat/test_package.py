#!/usr/bin/env python
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import sys

import pycosat
import test_pycosat

assert pycosat.__version__ == sys.argv[1]

assert test_pycosat.run().wasSuccessful()

assert test_pycosat.process_cnf_file("qg3-08.cnf") == 18
assert test_pycosat.process_cnf_file("uf20-098.cnf") == 5

import sudoku

sudoku.test()
