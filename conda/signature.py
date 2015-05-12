import base64
import hashlib

from conda.compat import PY3

from Crypto.PublicKey import RSA


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


def verify(path, key, sig):
    return key.verify(hash_file(path),
                      (ascii2sig(sig),))


def verify_keys(path, sig):
    """
    """
    for key in KEYS:
        if verify(path, key, sig):
            pass
