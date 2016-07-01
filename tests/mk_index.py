import os
import sys
import json

from conda.api import get_index


assert os.getenv('CIO_TEST') == '2'
assert tuple.__itemsize__ == 8
assert sys.platform.startswith('linux')

index = get_index()
for info in index.itervalues():
    for key in 'md5', 'size', 'channel', 'build_channel', 'build_target':
        try:
            del info[key]
        except KeyError:
            pass

print(len(index))

data = json.dumps(index, indent=2, sort_keys=True)
data = '\n'.join(line.rstrip() for line in data.splitlines())
if not data.endswith('\n'):
    data += '\n'
with open('index.json', 'w') as fo:
    fo.write(data)
