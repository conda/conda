'''
Created on Jan 16, 2014

@author: sean
'''
import os
_setuptools_data = None

def load_setuptools(env):
    global _setuptools_data
    
    if _setuptools_data is None:
        _setuptools_data = {} 
        def setup(**kw):
            _setuptools_data.update(kw)
        
        import setuptools
        #Patch setuptools
        setuptools_setup = setuptools.setup
        setuptools.setup = setup
        execfile('setup.py')
        setuptools.setup = setuptools_setup
    
    return _setuptools_data
     
    
def context_processor():
    return {'load_setuptools': load_setuptools}