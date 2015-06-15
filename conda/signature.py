import sys
import base64
import hashlib
from os.path import abspath, expanduser, isfile, join

from conda.compat import PY3

try:
    from Crypto.PublicKey import RSA
except ImportError:
    sys.exit("""\
Error: could not import Crypto (required for signature verification).
    Run the following command:

    $ conda install -n root pycrypto
""")

KEYS = {}
KEYS_DIR = abspath(expanduser('~/.conda/keys'))


def hash_file(path):
    h = hashlib.new('sha256')
    with open(path, 'rb') as fi:
        while True:
            chunk = fi.read(262144)  # process chunks of 256KB
            if not chunk:
                break
            h.update(chunk)
    return h.digest()


def sig2ascii(i):
    """
    Given a positive integer `i`, return a base64 encoded string
    representation of the value.
    """
    if i < 0:
        raise ValueError('positive integer expected, got: %r' % i)
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
    """
    Given the base64 encoded string representation of an integer (returned
    by sig2ascii), return the integer value.
    """
    res = 0
    for c in base64.b64decode(s):
        res *= 256
        res += (c if PY3 else ord(c))
    return res


class SignatureError(Exception):
    pass


def verify(path):
    """
    Verify the file `path`, with signature `path`.sig, against the key
    found under ~/.conda/keys/<key_name>.pub.  This function returns:
      - True, if the signature is valid
      - False, if the signature is invalid
      - None, when the signature or public key is not found
    """
    sig_path = path + '.sig'
    if not isfile(sig_path):
        raise SignatureError("signature does not exist: %s" % sig_path)
    with open(sig_path) as fi:
        key_name, sig = fi.read().split()
    if key_name not in KEYS:
        key_path = join(KEYS_DIR, '%s.pub' % key_name)
        if not isfile(key_path):
            raise SignatureError("public key does not exist: %s" % key_path)
        KEYS[key_name] = RSA.importKey(open(key_path).read())
    key = KEYS[key_name]
    return key.verify(hash_file(path), (ascii2sig(sig),))
