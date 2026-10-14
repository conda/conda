# Release news fragments (`releases/news/`)

## When to add

Add one file for each significant user-facing change for the next release: enhancements, bug fixes, deprecations, docs updates, removals.

Not needed for pure CI/typing/internal changes.

## How

- Copy `releases/news/TEMPLATE`.
- Filename: `<issue-number>-<short-slug>` (e.g. `16497-qa-snippets`).
- Use imperative mood (`Add`, `Fix`, `Remove`, `Mark`).
- Sections: Enhancements, Bug fixes, Deprecations, Docs, Other.

## Release lifecycle

Files here are aggregated into `CHANGELOG.md` when the release is cut. After cut, this directory is cleared (leaving only `TEMPLATE` and this `README.md`).

## References

- Agent conventions and detailed rules: `AGENTS.md` ("Changelog (`releases/news/`)")
- Release process: `RELEASE.md`
- Template: `releases/news/TEMPLATE`
