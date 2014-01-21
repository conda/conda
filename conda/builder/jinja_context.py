'''
Created on Jan 16, 2014

@author: sean
'''
from __future__ import print_function

import os
from conda.builder import environ
import json
_setuptools_data = None

def load_setuptools():
    global _setuptools_data
    
    if _setuptools_data is None:
        _setuptools_data = {} 
        def setup(**kw):
            _setuptools_data.update(kw)
        
        import setuptools
        #Patch setuptools
        setuptools_setup = setuptools.setup
        setuptools.setup = setup
        exec(open('setup.py').read())
        setuptools.setup = setuptools_setup
    
    return _setuptools_data
     
def load_npm():
    with open('package.json') as pkg:
        return json.load(pkg)

def context_processor():
    ctx = environ.get_dict()
    ctx.update(load_setuptools=load_setuptools,
               load_npm=load_npm,
               environ=os.environ)
    return ctx
