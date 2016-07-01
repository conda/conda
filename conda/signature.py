from __future__ import absolute_import, division, print_function

import base64
from os.path import abspath, expanduser, isfile, join
from .exceptions import CondaImportError
try:
    from Crypto.Hash import SHA256
    from Crypto.PublicKey import RSA
    from Crypto.Signature import PKCS1_PSS
except ImportError:
    raise CondaImportError("""\
Error: could not import Crypto (required for signature verification).
    Run the following command:

    $ conda install -n root pycrypto
""")

KEYS = {}
KEYS_DIR = abspath(expanduser('~/.conda/keys'))


def hash_file(path):
    h = SHA256.new()
    with open(path, 'rb') as fi:
        while True:
            chunk = fi.read(262144)  # process chunks of 256KB
            if not chunk:
                break
            h.update(chunk)
    return h


class SignatureError(Exception):
    pass


def verify(path):
    """
    Verify the file `path`, with signature `path`.sig, against the key
    found under ~/.conda/keys/<key_name>.pub.  This function returns:
      - True, if the signature is valid
      - False, if the signature is invalid
    It raises SignatureError when the signature file, or the public key
    does not exist.
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
    verifier = PKCS1_PSS.new(key)
    return verifier.verify(hash_file(path), base64.b64decode(sig))
