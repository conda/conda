import base64
import hashlib

from conda.compat import PY3

from Crypto.PublicKey import RSA


KEY = RSA.importKey("""\
-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDP2EHuYMftjf3dYODMif1s1eWj
7+He5Y7LYaH27E6Kw3vr/yaY6R6G1AjyAPD+7i13AjSjYPeNfNmTk99HbYJFIX3M
i+muS+7yOU9ItobZ/4btJbN/HScR9jPKBv3V/1QEjhFbtNNUoeZz9xZYgbkDrJo4
O4NaRivYsorIPxK37QIDAQAB
-----END PUBLIC KEY-----
""")


def ascii2sig(s):
    res = 0
    for c in base64.b64decode(s):
        res *= 256
        res += (c if PY3 else ord(c))
    return res


def hash_index(index):
    h = hashlib.new('sha256')
    for fn in sorted(index):
        h.update('%s  %s\n' % (index[fn]['md5'], fn))
    return h.hexdigest()


def verify_repodata(repodata):
    index = repodata['packages']
    try:
        sig = repodata['info']['signature']
    except KeyError:
        return "NO_SIGNATURE"
    if KEY.verify(hash_index(index), (ascii2sig(sig),)):
        return "VALID"
    else:
        return "INVALID"
