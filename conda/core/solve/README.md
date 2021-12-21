# Trying solvers

The new libmamba integrations are experimental, but you can get a taste of how they are working
so far by following these instructions.

1. Clone `conda/conda` and checkout the branch you want to try. `poc-libsolv` is the "stable
feature branch", but there might be other ones that are interesting to test. Check the opened
PRs to see.

```
git clone https://github.com/conda/conda
cd conda/
git checkout poc-libsolv
```

2. Build the Docker image:

```
docker compose build --no-cache interactive
```

3. Run the interactive console. This will preinitialize the image for `conda` in `dev` mode,
which means that:
    * The `conda` repository will be mounted to `/opt/conda-src``
    * The default `base` environment will run off this development install of `conda`!

```
docker compose run interactive
```

4. Now you can experiment different things. `--dry-run` is specially useful to check how different
solvers interact. The main switch you need to take care of is the _solver logic_ option:

```bash
# Using default (classic) solver
$ conda create -n demo scipy --dry-run
# This is equivalent
$ CONDA_SOLVER_LOGIC=classic conda create -n demo scipy --dry-run
# Using original libmamba integrations
$ CONDA_SOLVER_LOGIC=libmamba conda create -n demo scipy --dry-run
# Using refactored libmamba
$ CONDA_SOLVER_LOGIC=libmamba2 conda create -n demo scipy --dry-run
```

> `mamba` is also available in case you want to compare our integrations with the original Mamba
> project: `mamba create -n demo scipy --dry-run`

5. Use `time` to measure how different solvers perform. Take into account that repodata retrieval is cached across attempts, so only consider timings after warming that up:

```bash
# Warm up the repodata cache
$ conda create -n demo scipy --dry-run
# Timings for original solver
$ time env CONDA_SOLVER_LOGIC=classic conda create -n demo scipy --dry-run
# Timings for libmamba integration
$ time env CONDA_SOLVER_LOGIC=libmamba2 conda create -n demo scipy --dry-run
```

> `conda create` commands will have similar performance because it's a very simple action! However,
> things change once you factor in existing environments. Simple commands like `conda install scipy`
> show ~2x speedups already.

6. If you need extra details on _why_ solvers are working in that way, increase verbosity. Output
might get too long for your terminal buffer, so consider using a pager like `less`:

```bash
# Verbosity can be 0, 1, 2 or 3
$ CONDA_VERBOSITY=1 CONDA_SOLVER_LOGIC=libmamba conda create -n demo scipy --dry-run  2>&1 | less
```
