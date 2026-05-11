# Contributor and agent conventions

Short reference for changelog entries, deprecations, and tests in **conda**. Details live in [CEP 8](https://conda.org/learn/ceps/cep-0008/) (releases) and [CEP 9](https://conda.org/learn/ceps/cep-0009/) (deprecations).

## Local development

Bootstrap and set up an environment for **development and testing** from the repository root:

- **Unix / macOS:** `. ./dev/start`
- **Windows:** `.\dev\start.bat`
- **Dev Container:** Open the repo with **[Dev Containers](https://containers.dev/)** using **`.devcontainer/`** (e.g. VS Code). That gives a reproducible setup and avoids host **conda** / user configuration skewing tests (channel priority, etc.).
- When interacting with GitHub (e.g. repos, issues, pull requests etc), make use of the [GitHub CLI tool](https://cli.github.com/) to efficiently query the GitHub API.
- When working with GitHub issues and pull requests, always follow the issue and pull request templates and other conventions native to the GitHub entity in question.

## Code style

- Org-wide Python style policies (imports, docstrings, typing, etc.) are summarized in the **[Conda Style Guide](https://github.com/conda/infrastructure/blob/main/STYLEGUIDE.md)** (`conda/infrastructure` on GitHub).
- **This repo** configures formatting and lint with **[Ruff](https://docs.astral.sh/ruff/)** in **`pyproject.toml`** and **`.pre-commit-config.yaml`** (`ruff format`, `ruff check`). Hooks are **[prek](https://prek.j178.dev/)**-compatible (drop-in for **[pre-commit](https://pre-commit.com/)**); assume **prek** / **pre-commit** is already set up locally—this document does not cover installing or enabling hooks. CI enforces the same checks if a change bypasses hooks.

## Changelog (`news/`)

- Add **one file per significant change** under **`news/`** at the repo root. Use a copy of **`news/TEMPLATE`** as the template. Do **not** edit **`CHANGELOG.md`** directly; releases fold in `news/` fragments.
- **Filenames:** Prefer the **issue** number (not the PR number), plus a short slug, e.g. `14157-remove-conda-utils-unix-path-to-win`.
- **Tone:** Read **`CHANGELOG.md`** for section headings, bullet style, and deprecation/removal wording.
- **Sections:** Enhancements, Bug fixes, Deprecations, Docs, Other. Put **removals with Deprecations**, not under Other. One snippet may span multiple sections when one PR covers several kinds of changes.
- **Bullets:** End each bullet with a GitHub reference in parentheses. Prefer an issue when there is one, e.g. `(#12345)`, `(#12345 via #12346)`. When "via" is used, the syntax is `#issue-number via #pr-number`. Several issues/PRs can be mentioned in the same parentheses; use commas to separate them. Use **imperative mood** (Add, Fix, Mark, Remove), matching recent entries.
- **Deprecations / removals:** Follow existing Deprecations bullets in **`CHANGELOG.md`** (symbol paths, “pending deprecation”, target removal version, replacement when applicable).

## Deprecation policy

- **Releases ([CEP 8](https://conda.org/learn/ceps/cep-0008/)):** CalVer `YY.MM.MICRO`. Regular releases are roughly bi-monthly. **Deprecation releases** are **March (`YY.3.x`)** and **September (`YY.9.x`)**.
- **Schedule ([CEP 9](https://conda.org/learn/ceps/cep-0009/)):** A feature goes **pending deprecation** → **deprecated** (in a **`YY.3.x`** or **`YY.9.x`** release, after pending was in at least **two regular** releases) → **removed** in the **next** deprecation release after that.
- **`remove_in` in code and text:** Set removal to the **deprecation release** where the API will actually be removed (e.g. `27.3`). Keep **news** bullets and API warnings on the same version.

## `conda.deprecations`

Implement API and behavior deprecations with **`conda.deprecations`**: import **`deprecated`** from `conda.deprecations` (see **`conda/deprecations.py`**). The handler compares the running version to **`deprecate_in`** and **`remove_in`** for pending vs active warnings.

Common uses: **`deprecated(...)`** (functions, methods, classes), **`.argument`**, **`.action`** (argparse), **`.module`**, **`.constant`**, **`.topic`**.

## Tests

- Prefer **clear names** and **small, focused** tests; the body should read as the spec.
- Keep **docstrings short**; long prose drifts from the code.
- Avoid **`assert expr, "message"`** when the message only repeats static explanation—use a **`#` comment** above the line if a reader needs a hint.
- **Exit codes / subprocess output:** Bare **`assert rc == 0`** (or similar) is often too terse for CI; include **stderr** in the message (e.g. **`assert rc == 0, f"conda {subcommand} failed ({rc}): {stderr}"`**, or the same shape for **`pip install`** / **`python`** subprocess probes) so failures stay actionable.
- **Keep failure messages compact:** Prefer **one line** for **`assert … , msg`** — squash the message as much as you can (e.g. **`stderr` alone**, or a short label plus **`stderr`**). **Multiline** custom messages are hard to scan; reserve them for rare cases where a single line truly cannot carry enough signal.
- Prefer **native and installed pytest fixtures** (e.g. **`monkeypatch`** for **`setenv`**, **`chdir`**, etc.). **Reuse shared conda fixtures** before adding bespoke setup—see **Finding fixtures** below.
- Use **`pytest-mock`**’s **`mocker`** instead of **`unittest.mock`** when you need mocks or patches (automatic teardown and idiomatic pytest usage).
- **`mocker.spy`** is worth knowing for **call observation** or when swapping behavior is unnecessary—it often fits before **`mocker.patch`** or **`monkeypatch.setattr`**. **`monkeypatch`** is still the right tool for **`setenv`**, **`chdir`**, and similar—not attribute mocks.
- Parameterize tests to reduce repetition.
- Don't use section comments or other dividers to group code.
- Don't use test classes to group tests; single functions are preferred.

### Finding fixtures

Do **not** maintain a name-by-name table here (it goes stale). Discover fixtures from code:

- **`tests/conftest.py`** — registers **`pytest_plugins`** (e.g. **`conda.testing.fixtures`**, **`conda.testing.gateways.fixtures`**, **`conda.testing.notices.fixtures`**, **`tests.fixtures_package_server`**) and defines more fixtures in this file.
- **`conda/testing/fixtures.py`**, **`conda/testing/gateways/fixtures.py`**, **`conda/testing/notices/fixtures.py`** — main shared implementations; search for **`@pytest.fixture`** to list names and behavior.
- **Elsewhere** — additional fixtures may live in **subtree `conftest.py` files** or test modules; prefer reusing a shared fixture from **`conda.testing.*`** or **`tests/conftest.py`** when one fits.

The **Writing tests** chapter under **`docs/source/dev-guide/writing-tests/`** has more context (e.g. **`pytest_plugins`** and the HTTP test server).
