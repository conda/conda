=================
Package verifiers
=================

Package verifiers inspect package archives before conda extracts them. Conda
copies the selected archive into a private staging directory in the package cache
without changing its filename. It validates each recorded size and SHA-256, or MD5
when SHA-256 is unavailable, against that staged file. Conda then passes each
verifier the selected package record or explicit match specification, the staged
archive path, and the archive's computed SHA-256. Conda extracts the same staged
file and publishes those verified bytes back to the selected cache path after
successful extraction. Every registered verifier must accept the archive for
extraction to proceed.

Verifiers run in name order for each archive, but different archives may be
verified concurrently, so callbacks must be thread-safe. Conda may verify the
same archive more than once during a command, so callbacks must also be
idempotent. Callbacks must not mutate the package record, explicit match
specification, or archive. Raise
:class:`conda.CondaError` or a subclass to reject a package with an expected error.
:class:`conda.exceptions.CondaVerificationError` is available for a general
verification failure. Conda reports any other exception as a failure in the named
verifier plugin.

As with other package-cache operations, do not run another command that modifies
the same package cache while package verification and extraction are in progress.

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
