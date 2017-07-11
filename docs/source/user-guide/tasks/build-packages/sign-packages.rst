=================
Signing a package
=================

:emphasis:`Preview release`

Conda can verify RSA signatures on conda packages, and
conda build can generate key pairs, sign conda packages
and add the required package metadata to the conda repository
index. Any key size is supported, and the default is 2048 bits.

Given any public/private key pair, you may sign any file using
the private key, and the other person who receives the file must
verify the signature against the public key to use the file. The
person verifying the signature is assured that the signature was
indeed created using the private key.

Signing requires the following to be installed:

* conda build.

* PyCrypto installed into the root environment.

Before signing, you should have the following knowledge and
experience:

* Experience with building conda packages.

* Experience in setting up your own conda repository using the
  ``conda index`` command.

* Familiarity with the basics of public/private key cryptography.

* Understanding of the concept of digital signatures.

To sign packages:

#. Create a public/private key pair. Each public/private key pair
   is assigned a name, which is stored in the signature file such
   that the client knows which public key to verify the signature
   against.

   EXAMPLE: With a public key named ``MyKey``::

     conda sign --keygen MyKey


#. Sign the packages by passing the conda packages that need to
   be signed to the ``conda sign`` command.

   EXAMPLE: To sign all packages in the Linux-64 directory::

     cd <repository>/linux-64
     conda sign *.tar.bz2

   NOTE: Replace ``<repository>`` with the path to your
   repository. You are not required to sign all conda packages.
   You may choose which ones you wish to sign.

   Next to all conda packages, ``.sig`` files appear.

#. To verify that the signatures are valid, run the conda sign
   verify command::

     conda sign --verify *.tar.bz2

#. To index the repository, create or update the ``repodata.json``
   file by runnin the ``conda index`` command::

     conda index


Using the signed package
===================================

To use the signed package, the client must have access to the
repository and must add the public key file to
their ``~/.conda/keys`` directory before installing the package.

EXAMPLE::

    mkdir -p ~/.conda/keys
    cp <some download folder>/foo.pub ~/.conda/keys

When the client tries to install the signed package using the
``conda`` command, conda attempts to verify the signature.

* Conda permits the installation if it finds the signature.
* Conda exits if the signature is invalid, the signature is
  not found or the public key is not installed.
