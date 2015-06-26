======================
Signing conda packages
======================

**PREVIEW RELEASE**

Conda has the ability to verify RSA signatures on conda packages, and conda-build can generate key pairs, sign conda packages, and add the required package metadata to the conda repository index. Any key size is supported, and the default is 2048 bits.

Given any public/private key pair, you may sign any file using the private key, and the other person who receives the file must verify the signature against the public key in order to use the file. The person verifying the signature is assured that the signature was indeed created using the private key.

Requirements
=============

- Conda build installed 
- PyCrypto installed into the root environment
- Experience with building conda packages
- Experience in setting up your own conda repository using the "conda index" command
- Familiarity with the basics of public/private key cryptography, and 
- Understanding of the concept of digital signatures.

Signing packages summary
========================

Building a signed conda package is done with the following steps:

#. Create the public/private key pair.
#. Sign the packages using the "conda sign" command.
#. Verify that the signatures are valid.
#. Index the repository.
#. Use the signed package.

Step one: Create the public/private key pair
============================================

First, create a public/private key pair.  Each public/private key pair is assigned a name, which is stored in the signature file, such that the client knows which public key to verify the signature against. In this example, the public key is named MyKey: 
::

    conda sign --keygen MyKey

NOTE: Replace "MyKey" with the actual name you wish to give your key pair. 

Step two: Sign the packages
===========================

Sign the packages by simply passing the conda packages that need to be signed to the "conda sign" command. Example, if you wish to sign all packages in the Linux-64 directory:
::

    cd <repository>/linux-64
    conda sign *.tar.bz2

You will notice `.sig` files next to all conda packages.  

NOTE: You are not required to sign all conda packages; you may choose which ones you wish to sign. 

Step three: Verify that the signatures are valid
================================================

To verify that the signatures are valid, run the conda sign verify command:
::

    conda sign --verify *.tar.bz2

Step four: Index the repository
===============================

Finally, run the `conda index` command to update (or create) the `repodata.json` file:
::

    conda index

This completes the signing of the conda repository. 

Step five: Use the signed package
===================================

In order to use the signed package, the client must have access to the repository, and must add the public key file to their `~/.conda/keys` directory before installing the package. For example:
::

    mkdir -p ~/.conda/keys
    cp <some download folder>/foo.pub ~/.conda/keys

When the client tries to install the signed package using the `conda` command, conda will attempt to verify the signature. 

- Conda will permit the installation if it finds the signature. 
- Conda will exit if (i) the signature is invalid (ii) the signature is not found or, (iii) the public key is not installed.
