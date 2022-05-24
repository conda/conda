===============================
Using non-standard certificates
===============================

Using conda behind a firewall may require using a non-standard
set of certificates, which requires custom settings.

If you are using a non-standard set of certificates, then the
requests package requires the setting of ``REQUESTS_CA_BUNDLE``.
If you receive an error with self-signed certifications, you may
consider unsetting ``REQUESTS_CA_BUNDLE`` as well as ``CURL_CA_BUNDLE`` and `disabling SSL verification <https://conda.io/projects/conda/en/latest/user-guide/configuration/disable-ssl-verification.html>`_
to create a conda environment over HTTP.

You may need to set the conda environment to use the root certificate
provided by your company rather than conda’s generic ones.

One workflow to resolve this on macOS is:

* Open Chrome, got to any website, click on the lock icon on the left
  of the URL. Click on «Certificate» on the dropdown. In the next window
  you see a stack of certificates. The uppermost (aka top line in window)
  is the root certificate (e.g. Zscaler Root CA).
* Open macOS keychain, click on «Certificates» and choose among the
  many certificates the root certificate that you just identified.
  Export this to any folder of your choosing.
* Convert this certificate with OpenSSL: ``openssl x509 -inform der -in /path/to/your/certificate.cer -out /path/to/converted/certificate.pem``
* For a quick check, set your shell to acknowledge the certificate: ``export REQUESTS_CA_BUNDLE=/path/to/converted/certificate.pem``
* To set this permanently, open your shell profile (e.g. ``.bashrc`` or ``.zshrc``) and add this line: ``export REQUESTS_CA_BUNDLE=/path/to/converted/certificate.pem.``
  Now exit your terminal/shell and reopen. Check again.
