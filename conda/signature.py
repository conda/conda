import sys
import base64
import hashlib
from os.path import abspath, basename, expanduser, join

from conda.compat import PY3

from Crypto.PublicKey import RSA


KEYS = {}
KEYS_DIR = abspath(expanduser('~/.conda/keys'))


def sig2ascii(i):
    ret = []
    while i:
        i, r = divmod(i, 256)
        ret.append(r)
    if PY3:
        s = bytes(n for n in ret[::-1])
    else:
        s = ''.join(chr(n) for n in ret[::-1])
    return base64.b64encode(s).decode('utf-8')


def ascii2sig(s):
    res = 0
    for c in base64.b64decode(s):
        res *= 256
        res += (c if PY3 else ord(c))
    return res


def hash_file(path):
    h = hashlib.new('sha256')
    with open(path, 'rb') as fi:
        while True:
            chunk = fi.read(262144)
            if not chunk:
                break
            h.update(chunk)
    return h.digest()


def verify_keys(path):
    """
    Verify the file `path`, against all keys found under ~/.conda/keys/*.pub
    """
    with open(path + '.sig') as fi:
        key_name, sig = fi.read().split()
    if key_name not in KEYS:
        key_path = join(KEYS_DIR, '%s.pub' % key_name)
        KEYS[key_name] = RSA.importKey(open(key_path).read())
    key = KEYS[key_name]
    h = hash_file(path)
    if not key.verify(h, (ascii2sig(sig),)):
        sys.exit("Signature for '%s' invalid." % basename(path))


if __name__ == '__main__':
    print(KEYS)
