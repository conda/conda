=============
Health Checks
=============

Conda doctor can be extended with the ``conda_health_checks`` plugin hook.
Write new health checks using this hook, install the plugins you wrote, and they
will run every time the ``conda doctor`` command is executed.

Basic Health Check
==================

A health check requires two components:

- **name**: A human-readable name for the health check
- **action**: A function that performs the check and prints results

Example of a basic health check:

.. code-block:: python

   from conda.plugins import hookimpl
   from conda.plugins.types import CondaHealthCheck
   from conda.base.constants import OK_MARK, X_MARK


   def my_check(prefix: str, verbose: bool) -> None:
       """Check something in the environment."""
       if everything_ok(prefix):
           print(f"{OK_MARK} Everything looks good!")
       else:
           print(f"{X_MARK} Found a problem.")


   @hookimpl
   def conda_health_checks():
       yield CondaHealthCheck(
           name="My Custom Check",
           action=my_check,
       )

Health Checks with Fixes
========================

Health checks can optionally provide a ``fixer`` function that repairs detected issues.
When a user runs ``conda doctor --fix``, the fixer function is called after the check.

The fixer function receives:

- **prefix**: The environment prefix path
- **args**: The parsed command-line arguments (includes ``dry_run``, ``yes``, etc.)

It should return an integer exit code (0 for success).

Example with a fix:

.. code-block:: python

   from conda.plugins import hookimpl
   from conda.plugins.types import CondaHealthCheck
   from conda.base.constants import OK_MARK, X_MARK
   from conda.base.context import context
   from conda.reporters import confirm_yn


   def my_check(prefix: str, verbose: bool) -> None:
       if is_broken(prefix):
           print(f"{X_MARK} Something is broken.")
       else:
           print(f"{OK_MARK} All good!")


   def my_fix(prefix: str, args) -> int:
       if not is_broken(prefix):
           print("Nothing to fix.")
           return 0

       print("Found issue to fix.")
       confirm_yn("Proceed with fix?", dry_run=context.dry_run)

       # Perform the fix
       do_repair(prefix)
       print("Fixed!")
       return 0


   @hookimpl
   def conda_health_checks():
       yield CondaHealthCheck(
           name="My Fixable Check",
           action=my_check,
           fixer=my_fix,
           summary="Check for broken things",
           fix="Repair broken things",
       )

The ``confirm_yn`` function handles dry-run mode automatically by raising
``DryRunExit`` when ``context.dry_run`` is True.

API Reference
=============

.. autoapiclass:: conda.plugins.types.CondaHealthCheck
   :members:
   :undoc-members:

.. autoapifunction:: conda.plugins.hookspec.CondaSpecs.conda_health_checks
