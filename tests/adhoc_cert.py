# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Save adhoc ssl certificate locally to avoid per-test-run overhead.

Based on werkzeug.serving (RSA implementation).
"""
# Copyright 2007 Pallets
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     Redistributions of source code must retain the above copyright notice,
#     this list of conditions and the following disclaimer.
#
#     Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions and the following disclaimer in the documentation
#     and/or other materials provided with the distribution.
#
#     Neither the name of the copyright holder nor the names of its contributors
#     may be used to endorse or promote products derived from this software
#     without specific prior written permission.
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from __future__ import annotations

import os
import typing
from datetime import datetime as dt
from datetime import timedelta, timezone

if typing.TYPE_CHECKING:
    from cryptography.x509 import Certificate


def generate_adhoc_ssl_pair(
    cn: str | None = None,
) -> tuple[Certificate, typing.Any]:
    try:
        from cryptography import x509
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
    except ImportError:
        raise TypeError(
            "Using ad-hoc certificates requires the cryptography library."
        ) from None

    backend = default_backend()
    pkey = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=backend
    )

    # pretty damn sure that this is not actually accepted by anyone
    if cn is None:
        cn = "*"

    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Dummy Certificate"),
            x509.NameAttribute(NameOID.COMMON_NAME, cn),
        ]
    )

    backend = default_backend()
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(pkey.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(dt.now(timezone.utc))
        .not_valid_after(dt.now(timezone.utc) + timedelta(days=365))
        .add_extension(x509.ExtendedKeyUsage([x509.OID_SERVER_AUTH]), critical=False)
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(cn)]), critical=False)
        .sign(pkey, hashes.SHA256(), backend)
    )
    return cert, pkey


def generate_adhoc_certificate():
    """Generates an adhoc SSL context for the development server."""
    import atexit
    import tempfile

    cert, pkey = generate_adhoc_ssl_pair()

    from cryptography.hazmat.primitives import serialization

    cert_handle, cert_file = tempfile.mkstemp()
    pkey_handle, pkey_file = tempfile.mkstemp()
    atexit.register(os.remove, pkey_file)
    atexit.register(os.remove, cert_file)

    os.write(cert_handle, cert.public_bytes(serialization.Encoding.PEM))
    os.write(
        pkey_handle,
        pkey.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ),
    )

    from pathlib import Path

    Path(cert_file).rename(Path(__file__).parent / "adhoc.crt")
    Path(pkey_file).rename(Path(__file__).parent / "adhoc.key")


if __name__ == "__main__":
    generate_adhoc_certificate()
