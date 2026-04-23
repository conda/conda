# Contributor and agent conventions

Short reference for changelog entries, deprecations, and tests in **conda**. Details live in [CEP 8](https://conda.org/learn/ceps/cep-0008/) (releases) and [CEP 9](https://conda.org/learn/ceps/cep-0009/) (deprecations).

## Local development

Bootstrap and set up an environment for **development and testing** from the repository root:

- **Unix / macOS:** `. ./dev/start`
- **Windows:** `.\dev\start.bat`

## Code style

- Org-wide Python style policies (imports, docstrings, typing, etc.) are summarized in the **[Conda Style Guide](https://github.com/conda/infrastructure/blob/main/infrastructure/STYLEGUIDE.md)** (`conda/infrastructure` on GitHub).
- **This repo** configures formatting and lint with **[Ruff](https://docs.astral.sh/ruff/)** in **`pyproject.toml`** and **`.pre-commit-config.yaml`** (`ruff format`, `ruff check`). Hooks are **[prek](https://prek.j178.dev/)**-compatible (drop-in for **[pre-commit](https://pre-commit.com/)**); assume **prek** / **pre-commit** is already set up locally—this document does not cover installing or enabling hooks. CI enforces the same checks if a change bypasses hooks.

## Changelog (`news/`)

- Add **one file per change** under **`news/`** at the repo root. Use **`news/TEMPLATE`**. Do **not** edit **`CHANGELOG.md`** directly; releases fold in `news/` fragments.
- **Filenames:** Prefer the **issue** number (not the PR number), plus a short slug, e.g. `14157-remove-conda-utils-unix-path-to-win`.
- **Tone:** Read **`CHANGELOG.md`** for section headings, bullet style, and deprecation/removal wording.
- **Sections:** Enhancements, Bug fixes, Deprecations, Docs, Other. Put **removals with Deprecations**, not under Other. One snippet may span multiple sections when one PR covers several kinds of changes.
- **Bullets:** End each bullet with a GitHub reference in parentheses. Prefer an issue when there is one, e.g. `(#12345)`, `(#12345 via #12346)`. Use **imperative mood** (Add, Fix, Mark, Remove), matching recent entries.
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
- Avoid **`assert expr, "message"`** — use a **`#` comment** above the line if needed.
- Prefer using **native and installed pytest fixtures**, e.g. **`monkeypatch`**.
- Prefer to **reuse tests wide fixtures**, and implement local fixtures if useful.
- Use **`pytest-mock`**’s **`mocker`** fixture instead of **`unittest.mock`**, if needed.
- Parameterize tests to reduce repetition.
- Don't use section comments or other dividers to group code.
