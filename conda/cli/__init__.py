import os.path, sys, inspect

path = os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile( inspect.currentframe() ))[0],"..")))
if path not in sys.path: sys.path.insert(0, path)

from main import main
