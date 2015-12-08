## Chagelog

If you need more details about the changes made visit the
[releases](https://github.com/conda/conda-env/releases) page
on Github. Every release commit has all the information about
the changes in the source code.

#### v 2.4.5 (12/08/15)

- Store quiet arg as True (default to False) (@faph, #201)
- Initial support for requirements.txt as env spec (@malev, #203)
- Fix PROMPT reverting to $P$G default (@tadeu, #208)
- Fix activation behavior on Win (keep root Scripts dir on PATH); improve behavior with paths containing spaces (@msarahan, #212)

#### v2.4.4 (10/26/15)

- Change environment's versions when uploading. (@ijstokes, #191)
- Support specifying environment by path, as well as by name. (@remram44, #60)
- activate.bat properly searches CONDA_ENVS_PATH for named environments. (@mikecroucher, #164)
- Add Library\\bin to path when activating environments. (@malev, #152)

#### v2.4.3 (10/18/15)

- Better windows compatibility
- Typos in documentation

#### v2.4.2 (08/17/15)

- Support Jupyter

#### v2.4.1 (08/12/15)

- Fix `create` bug

#### v2.4.0 (08/11/15)

- `update` works with remote definitions
- `CONDA_ENV_PATH` fixed
- Windows prompt fixed
- Update `pip` dependencies
- `Library/bin` add to path in win
- Better authorization message
- Remove `--force` flag from upload
- New version created every time you run upload
- Using `conda_argparse2` now
- Fix `activate` script in ZSH
- `--no-builds` flag in attach
- Create environment from notebooks

#### v2.3.0 (07/09/15)

- `--force` flag on `create`
- `--no-builds` flag on `export`
- `conda env attach` feature

#### v2.2.3 (06/18/15)

- Reimplement `-n` flag

#### v2.2.2 (06/16/15)

- Allow `--force` flag on upload

#### v2.2.1 (6/8/15)

- Fix py3 issue with exceptions

### v2.2.0 (6/15/15)

- Create environment from remote definitions
- Upload environment definitions to anaconda.org
