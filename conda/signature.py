import sys
import base64
from os.path import abspath, expanduser, join

from conda.compat import PY3
from conda.utils import hashsum_file

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


def sig2ascii(i):
    """
    Given a positive integer `i`, return a base64 encoded string
    representation of the value.    
    """
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


def hash_file(path):
    return hashsum_file(path, mode='sha256')


def verify(path):
    """
    Verify the file `path`, with signature `path`.sig, against the key
    found under ~/.conda/keys/<key_name>.pub
    """
    try:
        with open(path + '.sig') as fi:
            key_name, sig = fi.read().split()
    except IOError:
        return 'NO_SIGATURE'
    if key_name not in KEYS:
        key_path = join(KEYS_DIR, '%s.pub' % key_name)
        try:
            KEYS[key_name] = RSA.importKey(open(key_path).read())
        except IOError:
            sys.exit("Error: no public key: %s" % key_path)
    key = KEYS[key_name]
    if key.verify(hash_file(path), (ascii2sig(sig),)):
        return 'VALID'
    else:
        return 'INVALID'
