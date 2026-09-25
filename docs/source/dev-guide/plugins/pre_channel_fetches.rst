===========================
Channel metadata pre-checks
===========================

The ``conda_pre_channel_fetches`` hook lets a provider check repository access
before the shared channel relation resolver reads JSON or shard metadata.
The hook receives each resolved ``Channel`` after native allowlist and denylist
validation. Raising an exception prevents that channel's metadata from being read.

Checks run once per channel in each resolver call, including explicit heads and
cached metadata. Setting ``channel_relations_max_depth`` to zero disables relation
discovery but still checks the explicit heads. Providers must not treat a previous
resolver call as authorization for later calls.

An explicit ``before_fetch`` callback passed to
``resolve_channels()`` runs before registered provider actions.
If it raises, no provider action or metadata read follows for that channel.
This lets a noninteractive caller require an existing repository decision before
a provider's normal interactive behavior can run.

This hook adds no transport implementation, configuration keys, or provider-specific
policy. Existing authentication, proxies, metadata caches, and offline behavior
remain in their native implementations. Direct artifact downloads from explicit
package records do not use this hook.

.. autoapiclass:: conda.plugins.types.CondaPreChannelFetch
   :members:
   :undoc-members:

.. autoapifunction:: conda.plugins.hookspec.CondaSpecs.conda_pre_channel_fetches
