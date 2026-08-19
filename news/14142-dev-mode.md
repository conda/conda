### Enhancements

* <news item>

### Bug fixes

* Do not force `context.dev` off when `--dev` is absent from `conda activate` / hook, so `CONDA_EXE` is retained across stacking and reactivate. (#14142 via #16571, #15696 via #16571)

### Deprecations

* Mark `conda activate --dev`, `conda create --dev`, `conda install --dev`, `conda remove --dev`, `conda init --dev`, `conda.base.context.Context.dev`, and `conda.utils.wrap_subprocess_call(dev_mode)` as pending deprecation, to be removed in 27.9. Conda will stop exporting `_CE_M` and `_CE_CONDA` except when `--dev` is passed; shell expansion of those variables remains. Set `PYTHONPATH` to the conda source root instead. (#14142 via #16571)

### Docs

* Note that `_CE_M` and `_CE_CONDA` in activation examples are empty no-ops. Use `PYTHONPATH` and `dev/start` for local conda development. (#14142 via #16571)

### Other

* <news item>
