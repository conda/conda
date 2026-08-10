=================
Package verifiers
=================

Package verifiers inspect package archives before conda extracts them. Conda
first validates the recorded size and SHA-256, or MD5 when SHA-256 is unavailable.
It then passes each verifier the selected package record or explicit match
specification, the archive path, and the archive's computed SHA-256. Every
registered verifier must accept the archive for extraction to proceed.

Verifiers run in name order for each archive, but different archives may be
verified concurrently, so callbacks must be thread-safe. Conda may verify the
same archive more than once during a command, so callbacks must also be
idempotent. Callbacks must not mutate the package record, explicit match
specification, or archive. Raise
:class:`conda.CondaError` or a subclass to reject a package with an expected error.
:class:`conda.exceptions.CondaVerificationError` is available for a general
verification failure. Conda reports any other exception as a failure in the named
verifier plugin.

Package verifier hooks run independently of the ``safety_checks`` setting. When at
least one verifier is registered, conda rechecks retained package archives instead
of reusing extracted package-cache entries without verification.

A plugin can enable verification by yielding a verifier only when its own setting
or environment variable is active. If no plugin yields a verifier, conda preserves
its normal package-cache behavior.

.. autoapiclass:: conda.plugins.types.CondaPackageVerifier
   :members:
   :undoc-members:

.. autoapifunction:: conda.plugins.hookspec.CondaSpecs.conda_package_verifiers
