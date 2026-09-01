# QA snippets (`releases/qa/`)

## When to add

Add a snippet only when a change needs manual blackbox testing that pytest cannot cover. Examples: user-visible CLI behavior, cross-platform/shell-specific behavior, real external integrations (canary/proxy/SSL/plugins), high-risk regression paths, security-sensitive paths.

Not needed when the change is fully covered by new or existing automated tests.

## How

- Copy `releases/qa/TEMPLATE`.
- Filename: `<issue-number>-<short-slug>`.
- Include concrete steps, prerequisites, pass criteria, and platform checkboxes.

## What not to include

- Pure docs, CI, or typing changes.
- Internal refactors with no user-observable change.
- Changes fully covered by `pytest` (including deprecations verified with `pytest.deprecated_call()`).

## Release lifecycle

Snippets are aggregated into the release QA plan issue when the release is cut. After cut, this directory is cleared (leaving only `TEMPLATE` and this `README.md`).

## References

- Agent conventions and criteria: `AGENTS.md` ("QA snippets (`releases/qa/`)")
- Release process: `RELEASE.md`
- Template: `releases/qa/TEMPLATE`
