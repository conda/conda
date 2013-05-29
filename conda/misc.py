import os
import sys
import json
from subprocess import check_call
from os.path import abspath, join



def launch(app_dir):
    with open(join(app_dir, 'meta.json')) as fi:
        meta = json.load(fi)
    # prepend the bin directory to the path
    fmt = r'%s\Scripts;%s' if sys.platform == 'win32' else '%s/bin:%s'
    env = {'PATH': fmt % (abspath(join(app_dir, '..', '..')),
                          os.getenv('PATH'))}
    # copy existing environment variables, but not anything with PATH in it
    for k, v in os.environ.iteritems():
        if 'PATH' not in k:
            env[k] = v
    # allow updating environment variables from metadata
    if 'env' in meta:
        env.update(meta['env'])
    # call the entry command
    check_call(meta['entry'].split(), cwd=app_dir, env=env)


if __name__ == '__main__':
    launch('/Users/ilan/python/App/filebin')
