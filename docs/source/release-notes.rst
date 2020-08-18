=============
Release notes
=============

This information is drawn from the GitHub conda project
changelog: https://github.com/conda/conda/blob/master/CHANGELOG.md

4.8.4 (2020-08-06)
==================

Enhancements
^^^^^^^^^^^^

* Add ``linux-ppc64`` as a recognized platform (#9797, #9877)
* Add ``linux-s390x`` as a recognized platform (#9933, #10051)
* Add spinner to pip installer (#10032)
* Add support for running conda in PyPy (#9764)
* Support creating conda environments using remote specification files (#9835)
* Allow request retries on various HTTP errors (#9919)
* Add ``compare`` command for environments against a specification file (#10022)
* Add (preliminary) support for JSON-format activation (#8727)
* Properly handle the ``CURL_CA_BUNDLE`` environment variable (#10078)
* More uniformly handle ``$CONDA_PREFIX`` when exporting environments (#10092)
* Enable trailing ``_`` to anchor OpenSSL-like versions (#9859)
* Replace ``listdir`` and ``glob`` with ``scandir`` (#9889)
* Ignore virtual packages when searching for constrained packages (#10117)
* Add virtual packages to be considered in the solver (#10057)

Bug fixes
^^^^^^^^^

* Prevent ``remove --all`` from deleting non-environment directories (#10086)
* Prevent ``create --dry-run --yes`` from deleting existing environments (#10090)
* Remove extra newline from environment export file (#9649)
* Print help on incomplete ``conda env config`` command rather than crashing (#9660)
* Correctly set exit code/errorlevel when ``conda run`` exits (#9665)
* Send "inconsistent environment" warnings to stderr to avoid breaking JSON output (#9738)
* Fix output formatting from post-link scripts (#9841)
* Fix URL parsing for channel subdirs (#9844)
* Fix ``conda env export -f`` sometimes producing empty output files (#9909)
* Fix handling of Python releases with two-digit minor versions (#9999)
* Do not use gid to determine if user is an admin on \*nix platforms (#10002)
* Suppress spurious xonsh activation warnings (#10005)
* Fix crash when running ``conda update --all`` on a nonexistent environment (#10028)
* Fix collections import for Python 3.8 (#10093)
* Fix regex-related deprecation warnings (#10093, #10096)
* Fix logic error when running under Python 2.7 on 64-bit platforms (#10108)
* Fix Python 3.8 leaked semaphore issue (#10115)

Docs
^^^^

* Fix formatting and typos (#9623, #9689, #9898, #10042)
* Correct location for yum repository configuration files (#9988)
* Clarify usage for the ``--channel`` option (#10054)
* Clarify Python is not installed by default into new environments (#10089)

Miscellaneous
^^^^^^^^^^^^^

* Fixes to tests and CI pipelines (#9842, #9863, #9938, #9960, #10010)
* Remove conda-forge dependencies for developing conda (#9857, #9871)
* Audit YAML usage for ``safe_load`` vs ``round_trip_load`` (#9902)

Contributors
^^^^^^^^^^^^

* @alanhdu
* @angloyna
* @Anthchirp
* @Arrowbox
* @bbodenmiller
* @beenje
* @bernardoduarte
* @birdsarah
* @bnemanich
* @chenghlee
* @ChihweiLHBird
* @cjmartian
* @ericpre
* @error404-beep
* @esc
* @hartb
* @hugobuddel
* @isuruf
* @jjhelmus
* @kalefranz
* @mingwandroid
* @mlline00
* @mparry
* @mrocklin
* @necaris
* @pdnm
* @pradghos
* @ravigumm
* @Reissner
* @scopatz
* @sidhant007
* @songmeixu
* @speleo3
* @tomsaleeba
* @WinstonPais


4.8.3 (2020-03-13)
==================

Docs
^^^^

* Add release notes for 4.8.2 to docs (#9632)
* Fix typos in docs (#9637, #9643)
* Grammatical and formatting changes (#9647)

Bug fixes
^^^^^^^^^

* Account for channel is specs (#9748)

Contributors
^^^^^^^^^^^^

* @bernardoduarte
* @forrestwaters
* @jjhelmus
* @msarahan
* @rrigdon
* @timgates42


4.8.2 (2020-01-24)
==================

Enhancements
^^^^^^^^^^^^

* Improved solver messaging  (#9560)

Docs
^^^^

* Added precedence and conflict info  (#9565)
* Added how to set env variables with config API  (#9536)
* Updated user guide, deleted Overview, minor clean up (#9581)
* Added code of conduct (#9601, #9602, #9603, #9603, #9604, #9605)

Bug fixes
^^^^^^^^^

* Change fish prompt only if changeps1 is true  (#7000)
* Make frozendict JSON serializable (#9539)
* Conda env create empty dir (#9543)


Contributors
^^^^^^^^^^^^

* @msarahan
* @jjhelmus
* @rrigdon
* @soapy1
* @teake
* @csoja
* @kfranz


4.8.1 (2019-12-19)
==================

Enhancements
^^^^^^^^^^^^

* Improve performance for conda run by avoiding Popen.communicate (#9381)
* Put conda keyring in /usr/share/keyrings on Debian (#9424)
* Refactor common.logic to fix some bugs and prepare for better modularity (#9427)
* Support nested configuration (#9449)
* Support Object configuration parameters (#9465)
* Use freeze_installed to speed up conda env update (#9511)
* Add networking args to conda env create (#9525)


Bug fixes
^^^^^^^^^

* Fix calling Python API run_command with list and string arguments (#9331)
* Set tmp to shortened path that excludes spaces (#9409)
* Add subdir to PackageRecord dist_str (#9418)
* Revert init bash completion (#9421)
* Avoid function redefinition upon resourcing conda.fish (#9444)
* Propagate PIP error level when creating envs with conda env (#9460)
* Fix incorrect chown call (#9464)
* Don't check in pkgs for trash (#9472)
* Fix running conda activate in multiple processes on Windows (#9477)
* Remove setuptools from run_constrained in recipe (#9485)
* Fix ``__conda_activate`` function to correctly return exit code (#9532)
* Fix overly greedy capture done by subprocess for conda run (#9537)


Docs
^^^^
* Fix string concatenation running words together regarding CONDA_EXE (#9411)
* Fix typo ("list" -> "info") (#9433)
* Improve description of DLL loading verification and activating environments (#9453)
* Installing with specific build number (#9534)
* Typo in condarc key envs_dirs (#9478)
* Clarify channel priority and package sorting (#9492)

Contributors
^^^^^^^^^^^^

* @AntoinePrv
* @brettcannon
* @bwildenhain
* @cjmartian
* @felker
* @forrestwaters
* @gilescope
* @isuruf
* @jeremyjliu
* @jjhelmus
* @jhultman
* @marcuscaisey
* @mbargull
* @mingwandroid
* @msarahan
* @okhoma
* @osamoylenko
* @rrigdon
* @rulerofthehuns
* @soapy1
* @tartansandal

4.8.0 (2019-11-04)
==================

Enhancements
^^^^^^^^^^^^

* Retry downloads if they fail, controlled by ``remote_max_retries`` and ``remote_backoff_factor`` configuration values (#9318)
* Redact authentication information in some URLs (#9341)
* Add osx version virtual package , ``__osx`` (#9349)
* Add glibc virtual package, ``__glibc`` (#9358)

Bug fixes
^^^^^^^^^

* Fix issues with xonsh activation on Windows (#8246)
* Remove unsupported --lock argument from conda clean (#8310)
* Do not add ``sys_prefix_path`` to failed activation or deactivation (#9282)
* Fix csh setenv command (#9284)
* Do not memorize ``PackageRecord.combined_depends`` (#9289)
* Use ``CONDA_INTERNAL_OLDPATH`` rather than ``OLDPATH`` in activation script (#9303)
* Fix xonsh activation and tab completion (#9305)
* Fix what channels are queried when context.offline is True (#9385)

Docs
^^^^

* Removed references to MD5s from docs (#9247)
* Add docs on ``CONDA_DLL_SEARCH_MODIFICATION_ENABLED`` (#9286)
* Document threads, spec history, and configuration (#9327)
* More documentation on channels (#9335)
* Document the .condarc search order (#9369)
* Various minor documentation fixes (#9238, #9248, #9267, #9334, #9351, #9372, #9378, #9388, #9391, #9393)

Contributors
^^^^^^^^^^^^

* @analog-cbarber
* @andreasg123
* @beckermr
* @bryant1410
* @colinbrislawn
* @felker
* @forrestwaters
* @gabrielcnr
* @isuruf
* @jakirkham
* @jeremyjliu
* @jjhelmus
* @jooh
* @jpigla
* @marcelotrevisani
* @melund
* @mfansler
* @mingwandroid
* @msarahan
* @rrigdon
* @scopatz
* @soapy1
* @WillyChen123
* @xhochy

4.7.12 (2019-09-12)
===================

Enhancements
^^^^^^^^^^^^

* Add support for env file creation based on explicit specs in history (#9093)
* Detect prefix paths when -p nor -n not given  (#9135)
* Add config parameter to disable conflict finding (for faster time to errors)  (#9190)

Bug fixes
^^^^^^^^^

* Fix race condition with creation of repodata cache dir  (#9073)
* Fix ProxyError expected arguments  (#9123)
* Makedirs to initialize .conda folder when registering env - fixes permission errors with .conda folders not existing when package cache gets created (#9215)
* Fix list duplicates errors in reading repodata/prefix data  (#9132)
* Fix neutered specs not being recorded in history, leading to unsatisfiable environments later  (#9147)
* Standardize "conda env list" behavior between platforms  (#9166)
* Add JSON output to conda env create/update  (#9204)
* Speed up finding conflicting specs (speed regression in 4.7.11)  (#9218)

Contributors
^^^^^^^^^^^^

* @beenje
* @Bezier89
* @cjmartian
* @forrestwaters
* @jjhelmus
* @martin-raden
* @msarahan
* @nganani
* @rrigdon
* @soapy1
* @WesRoach
* @zheaton


4.7.11 (2019-08-06)
===================

Enhancements
^^^^^^^^^^^^

* Add config for control of number of threads.
  These can be set in condarc or using environment variables.
  Names/default values are: ``default_threads/None``, ``repodata_threads/None``, ``verify_threads/1``, ``execute_threads/1`` (#9044)

Bug fixes
^^^^^^^^^

* Fix repodata_fns from condarc not being respected (#8998)
* Fix handling of UpdateModifiers other than FREEZE_INSTALLED (#8999)
* Improve conflict finding graph traversal (#9006)
* Fix setuptools being removed due to conda run_constrains (#9014)
* Avoid calling find_conflicts until all retries are spent (#9015)
* Refactor _conda_activate.bat in hopes of improving behavior in parallel environments (#9021)
* Add support for local version specs in PYPI installed packages (#9025)
* Fix boto3 initialization race condition (#9037)
* Fix return condition in package_cache_data (#9039)
* Utilize libarchive_enabled attribute provided by conda-package-handling to fall back to .tar.bz2 files only. (#9041, #9053)
* Fix menu creation on Windows having race condition, leading to popups about python.exe not being found (#9044)
* Improve list error when egg-link leads to extra egg-infos (#9045)
* Fix incorrect RemoveError when operating on an env that has one of conda's deps, but is not the env in which the current conda in use resides (#9054)

Docs
^^^^

* Document new package format better
* Document ``conda init`` command
* Document availability of RSS feed for CDN-backed channels that clone

Contributors
^^^^^^^^^^^^

* @Bezier89
* @forrestwaters
* @hajapy
* @ihnorton
* @matthewwardrop
* @msarahan
* @rogererens
* @rrigdon
* @soapy1


4.7.10 (2019-07-19)
===================


Bug fixes
^^^^^^^^^

* Fix merging of specs
* Fix bugs in building of chains in prefix graph

Contributors
^^^^^^^^^^^^

* @msarahan


4.7.9 (2019-07-18)
==================

Bug fixes
^^^^^^^^^

* Fix Non records in comprehension
* Fix potential keyerror in depth-first search
* Fix PackageNotFound attribute error

Contributors
^^^^^^^^^^^^

* @jjhelmus
* @msarahan


4.7.8 (2019-07-17)
==================

Improvements
^^^^^^^^^^^^
* Improve unsatisfiable messages - try to group and explain output better.  Remove lots of extraneous stuff that was showing up in 4.7.7 (#8910)
* Preload openssl on Windows to avoid library conflicts and missing library issues (#8949)


Bug fixes
^^^^^^^^^

* Fix handling of channels where more than one channel contains packages with similar name, subdir, version, and build_number.  This was causing mysterious unsatisfiable errors for some users.  (#8938)
* Reverse logic check in checking channel equality, because == is not reciprocal to != with py27 (no ``__ne__``) (#8938)
* Fix an infinite loop or otherwise large process with building the unsatisfiable info.  Improve the depth-first search implementation.  (#8941)
* Streamline fallback paths to unfrozen solve in case frozen fails. (#8942)
* Environment activation output only shows ``conda activate envname`` now, instead of sometimes showing just ``activate``.  (#8947)

Contributors
^^^^^^^^^^^^

* @forrestwaters
* @jjhelmus
* @katietz
* @msarahan
* @rrigdon
* @soapy1



4.7.7 (2019-07-12)
==================

Improvements
^^^^^^^^^^^^

* When an update command doesn't do anything because installed software conflicts with the update, information about the conflict is shown, rather than just saying "all requests are already satisfied"  (#8899)


Bug fixes
^^^^^^^^^

* Fix missing package_type attr in finding virtual packages  (#8917)
* Fix parallel operations of loading index to preserve channel ordering  (#8921, #8922)
* Filter PrefixRecords out from PackageRecords when making a graph to show unsatisfiable deps.  Fixes comparison error between mismatched types.  (#8924)
* Install entry points before running post-link scripts, because post-link scripts may depend on entry points.  (#8925)


Contributors
^^^^^^^^^^^^

* @jjhelmus
* @msarahan
* @rrigdon
* @soapy1


4.7.6 (2019-07-11)
==================

Improvements
^^^^^^^^^^^^

* Improve cuda virtual package conflict messages to show the `__cuda` virtual package as part of the conflict (#8834)
* Add additional debugging info to Resolve.solve (#8895)

Bug fixes
^^^^^^^^^

* Deduplicate error messages being shown for post-link scripts.  Show captured stdout/stderr on failure  (#8833)
* Fix the checkout step in the Windows dev env setup instructions (#8827)
* Bail out early when implicit Python pinning renders an explicit spec unsatisfiable (#8834)
* Handle edge cases in pinned specs better (#8843)
* Extract package again if url is None (#8868)
* Update docs regarding indexing and subdirs (#8874)
* Remove warning about conda-build needing an update that was bothering people (#8884)
* Only add repodata fn into cache key when fn is not repodata.json (#8900)
* Allow conda to be downgraded with an explicit spec (#8892)
* Add target to specs from historic specs (#8901)
* Improve message when solving with a repodata file before repodata.json fails (#8907)
* Fix distutils usage for "which" functionality.  Fix inability to change Python version in envs with noarch packages (#8909)
* Fix Anaconda metapackage being removed because history matching was too restrictive (#8911)
* Make freezing less aggressive; add fallback to non-frozen solve (#8912)

Contributors
^^^^^^^^^^^^

* @forrestwaters
* @jjhelmus
* @mcopes73
* @msarahan
* @richardjgowers
* @rrigdon
* @soapy1
* @twinssbc

4.7.5 (2019-06-24)
==================

Improvements
^^^^^^^^^^^^

* Improve wording in informational message when a particular
  `*_repodata.json` can't be found.  No need for alarm.  (#8808)

Bug fixes
^^^^^^^^^

* Restore tests being run on win-32 appveyor  (#8801)
* Fix Dist class handling of .conda files  (#8816)
* Fix strict channel priority handling when a package is unsatisfiable and thus not present in the collection  (#8819)
* Handle JSONDecodeError better when package is corrupted at extract time  (#8820)

Contributors
^^^^^^^^^^^^

* @dhirschfeld
* @msarahan
* @rrigdon

4.7.4 (2019-06-19)
==================

Improvements
^^^^^^^^^^^^

* Revert to and improve the unsatisfiability determination from 4.7.2 that was reverted in 4.7.3.  It's faster.  (#8783)

Bug fixes
^^^^^^^^^

* Fix tcsh/csh init scripts  (#8792)

Docs improvements
^^^^^^^^^^^^^^^^^

* Clean up docs of run_command
* Fix broken links
* Update docs environment.yaml file to update conda-package-handling
* Conda logo favicon
* Update strict channel priority info
* Noarch package content ported from conda-forge
* Add info about conda-forge
* Remove references to things as they were before conda 4.1.  That was a long time ago.  This is not a history book.

Contributors
^^^^^^^^^^^^

* @jjhelmus
* @msarahan
* @rrigdon
* @soapy1


4.7.3 (2019-06-14)
==================

Bug fixes
^^^^^^^^^

* Target prefix overrid applies to entry points in addition to replacements in standard files  (#8769)
* Revert to solver-based unsatisfiability determination  (#8775)
* Fix renaming of existing prompt function in powershell  (#8774)


Contributors
^^^^^^^^^^^^

* @jjhelmus
* @msarahan
* @rrigdon
* @ScottEvtuch


4.7.2 (2019-06-10)
==================

Behavior changes
^^^^^^^^^^^^^^^^

* Unsatisfiability is determined in a slightly different way now. It no longer
  uses the SAT solver, but rather determines whether any specs have no
  candidates at all after running through get_reduced_index. This has been
  faster in benchmarks, but we welcome further data from your use cases about
  whether this was a good change.  (#8741)
* When using the --only-deps flag for the `install` command, conda now
  explicitly records those specs in your history. This primarily serves to
  reduce conda accidentally removing packages that you have actually requested.  (#8766)
  

Improvements
^^^^^^^^^^^^

* UnsatisfiableError messages are now grouped into categories and explained a bit better.  (#8741)
* --repodata-fn argument can be passed multiple times to have more fallback
  paths. `repodata_fns` conda config setting does the same thing, but saves you
  from needing to do it for every command invocation.  (#8741)


Bug fixes
^^^^^^^^^

* Fix channel flip-flopping that was happening when adding a channel other than earlier ones  (#8741)
* Refactor flow control for multiple repodata files to not use exceptions  (#8741)
* Force conda to use only old .tar.bz2 files if conda-build <3.18.3 is
  installed. Conda-build breaks when inspecting file contents; this is fixed
  in conda-build 3.18.3 (#8741)
* Use --force when using rsync to improve behavior with folders that may exist
  in the destination somehow. (#8750)
* Handle EPERM errors when renaming, because MacOS lets you remove or create
  files, but not rename them. Thanks, Apple. (#8755)
* Fix conda removing packages installed via `install` with --only-deps flag when
  either `update` or `remove` commands are run. See behavior changes above.
  (#8766)

Contributors
^^^^^^^^^^^^

* @csosborn
* @jjhelmus
* @katietz
* @msarahan
* @rrigdon

4.7.1 (2019-05-30)
==================

Improvements
^^^^^^^^^^^^

* Base initial solver specs map on explicitly requested specs (new and historic)  (#8689)
* Improve anonymization of automatic error reporting  (#8715)
* Add option to keep using .tar.bz2 files, in case new .conda isn't working for whatever reason  (#8723)

Bug fixes
^^^^^^^^^

* Fix parsing hyphenated PyPI specs (change hyphens in versions to .)  (#8688)
* Fix PrefixRecord creation when file inputs are .conda files  (#8689)
* Fix PrefixRecord creation for pip-installed packages  (#8689)
* Fix progress bar stopping at 75% (no extract progress with new libarchive)  (#8689)
* Preserve pre-4.7 download() interface in conda.exports  (#8698)
* Virtual packages (such as cuda) are represented by leading double underscores
  by convention, to avoid confusion with existing single underscore packages
  that serve other purposes (#8738)

Deprecations/Breaking changes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* The `--prune` flag no longer does anything. Pruning is implicitly the
  standard behavior now as a result of the initial solver specs coming from
  explicitly requested specs. Conda will remove packages that are not explicitly
  requested and are not required directly or indirectly by any explicitly
  installed package.

Docs improvements
^^^^^^^^^^^^^^^^^

* Document removal of the `free` channel from defaults (#8682)
* Add reference to conda config --describe  (#8712)
* Add a tutorial for .condarc modification  (#8737)

Contributors
^^^^^^^^^^^^

* @alexhall
* @cjmartian
* @kalefranz
* @martinkou
* @msarahan
* @rrigdon
* @soapy1


4.7.0 (2019-05-17)
==================

Improvements
^^^^^^^^^^^^

* Implement support for "virtual" CUDA packages, to make conda consider the system-installed CUDA driver and act accordingly  (#8267)
* Support and prefer new .conda file format where available  (#8265, #8639)
* Use comma-separated env names in prompt when stacking envs  (#8431)
* show valid choices in error messages for enums  (#8602)
* freeze already-installed packages when running `conda install` as a first attempt, to speed up the solve in existing envs.  Fall back to full solve as necessary  (#8260, #8626)
* Add optimization criterion to prefer arch over noarch packages when otherwise equivalent  (#8267)
* Remove `free` channel from defaults collection.  Add `restore_free_channel` config parameter if you want to keep it.  (#8579)
* Improve unsatisfiable hints  (#8638)
* Add capability to use custom repodata filename, for smaller subsets of repodata  (#8670)
* Parallelize SubdirData readup  (#8670)
* Parallelize transacation verification and execution  (#8670)

Bug fixes
^^^^^^^^^

* Fix PATH handling with deactivate.d scripts  (#8464)
* Fix usage of deprecated collections ABCs (#)
* Fix tcsh/csh initialization block  (#8591)
* Fix missing CWD display in powershell prompt  (#8596)
* `wrap_subprocess_call`: fallback to sh if no bash  (#8611)
* Fix `TemporaryDirectory` to avoid importing from `conda.compat`  (#8671)
* Fix missing conda-package-handling dependency in dev/start  (#8624)
* Fix `path_to_url` string index out of range error  (#8265)
* Fix conda init for xonsh  (#8644)
* Fix fish activation (#8645)
* Improve error handling for read-only filesystems  (#8665, #8674)
* Break out of minimization when bisection has nowhere to go  (#8672)
* Handle None values for link channel name gracefully  (#8680)

Contributors
^^^^^^^^^^^^

* @chrisburr
* @EternalPhane
* @jjhelmus
* @kalefranz
* @mbargull
* @msarahan
* @rrigdon
* @scopatz
* @seibert
* @soapy1
* @nehaljwani
* @nh3
* @teake
* @yuvalreches

4.6.14 (2019-04-17)
===================

Bug fixes
^^^^^^^^^

* Export extra function in powershell Conda.psm1 script (fixes Anaconda powershell prompt)  (#8570)

Contributors
^^^^^^^^^^^^

* @msarahan


4.6.13 (2019-04-16)
===================

Bug fixes
^^^^^^^^^

* Disable ``test_legacy_repodata`` on win-32 (missing dependencies)  (#8540)
* Fix activation problems on windows with bash, powershell, and batch.  Improve tests. (#8550, #8564)
* Pass -U flag to for pip dependencies in conda env when running "conda env update"  (#8542)
* Rename ``conda.common.os`` to ``conda.common._os`` to avoid shadowing os built-in  (#8548)
* Raise exception when pip subprocess fails with conda env  (#8562)
* Fix installing recursive requirements.txt files in conda env specs with Python 2.7  (#8562)
* Don't modify powershell prompt when "changeps1" setting in condarc is False  (#8465)

Contributors
^^^^^^^^^^^^

* @dennispg
* @jjhelmus
* @jpgill86
* @mingwandroid
* @msarahan
* @noahp


4.6.12 (2019-04-10)
===================

Bug fixes
^^^^^^^^^

* Fix compat import warning (#8507)
* Adjust collections import to avoid deprecation warning (#8499)
* Fix bug in CLI tests (#8468)
* Disallow the number sign in environment names (#8521)
* Workaround issues with noarch on certain repositories (#8523)
* Fix activation on Windows when spaces are in path (#8503)
* Fix conda init profile modification for powershell (#8531)
* Point conda.bat to condabin (#8517)
* Fix various bugs in activation (#8520, #8528)

Docs improvements
^^^^^^^^^^^^^^^^^

* Fix links in README (#8482)
* Changelogs for 4.6.10 and 4.6.11 (#8502)

Contributors
^^^^^^^^^^^^

* @Bezier89
* @duncanmmacleod
* @ivigamberdiev
* @javabrett
* @jjhelmus
* @katietz
* @mingwandroid
* @msarahan
* @nehaljwani
* @rrigdon


4.6.11 (2019-04-04)
===================

Bug fixes
^^^^^^^^^

* Remove sys.prefix from front of PATH in basic_posix (#8491)
* Add import to fix conda.core.index.get_index (#8495)

Docs improvements
^^^^^^^^^^^^^^^^^

* Changelogs for 4.6.10

Contributors
^^^^^^^^^^^^

* @jjhelmus
* @mingwandroid
* @msarahan


4.6.10 (2019-04-01)
===================

Bug fixes
^^^^^^^^^

* Fix Python-3 only FileNotFoundError usage in initialize.py  (#8470)
* Fix more JSON encode errors for the _Null data type (#8471)
* Fix non-posix-compliant == in conda.sh  (#8475, #8476)
* Improve detection of pip dependency in environment.yml files to avoid warning message  (#8478)
* Fix condabin\conda.bat use of dp0, making PATH additions incorrect  (#8480)
* init_fish_user: don't assume config file exists  (#8481)
* Fix for chcp output ending with . (#8484)

Docs improvements
^^^^^^^^^^^^^^^^^

* Changelogs for 4.6.8, 4.6.9

Contributors
^^^^^^^^^^^^

* @duncanmmacleod
* @nehaljwani
* @ilango100
* @jjhelmus
* @mingwandroid
* @msarahan
* @rrigdon


4.6.9 (2019-03-29)
==================

Improvements
^^^^^^^^^^^^

* Improve CI for docs commits  (#8387, #8401, #8417)
* Implement `conda init --reverse` to undo rc file and registry changes  (#8400)
* Improve handling of unicode systems  (#8342, #8435)
* Force the "COMSPEC"  environment variable to always point to cmd.exe on Windows.
  This was an implicit assumption that was not always true.  (#8457, #8461)

Bug fixes
^^^^^^^^^

* Add central C:/ProgramData/conda as a search path on Windows  (#8272)
* Remove direct use of ruamel_yaml (prefer internal abstraction, yaml_load)  (#8392)
* Fix/improve `conda init` support for fish shell  (#8437)
* Improve solver behavior in the presence of inconsistent environments (such as pip as a conda dependency of Python, but also installed via pip itself) (#8444)
* Handle read-only filesystems for environments.txt  (#8451, #8453)
* Fix conda env commands involving pip-installed dependencies being installed into incorrect locations  (#8435)


Docs improvements
^^^^^^^^^^^^^^^^^

* Updated cheatsheet  (#8402)
* Updated color theme  (#8403)


Contributors
^^^^^^^^^^^^

* @blackgear
* @dhirschfeld
* @jakirkham
* @jjhelmus
* @katietz
* @mingwandroid
* @msarahan
* @nehaljwani
* @rrigdon
* @soapy1
* @spamlrot-tic


4.6.8 (2019-03-06)
==================

Bug fixes
^^^^^^^^^

* Detect when parser fails to parse arguments  (#8328)
* Separate post-link script running from package linking. Do linking of all packages first, then run any post-link 
  scripts after all packages are present. Ideally, more forgiving in presence of cycles.  (#8350)
* Quote path to temporary requirements files generated by conda env. Fixes issues with spaces.  (#8352)
* Improve some exception handling around checking for presence of folders in extraction of tarballs  (#8360)
* Fix reporting of packages when channel name is None  (#8379)
* Fix the post-creation helper message from "source activate" to "conda activate" (#8370)
* Add safety checks for directory traversal exploits in tarfiles. These may be disabled using the ``safety_checks`` 
  configuration parameter.  (#8374)


Docs improvements
^^^^^^^^^^^^^^^^^

* Document MKL DLL hell and new Python env vars to control DLL search behavior  (#8315)
* Add Github template for reporting speed issues  (#8344)
* Add in better use of Sphinx admonitions (notes, warnings) for better accentuation in docs  (#8348) 
* Improve skipping CI builds when only docs changes are involved  (#8336)


Contributors
^^^^^^^^^^^^

* @albertmichaelj
* @jjhelmus
* @matta9001
* @msarahan
* @rrigdon
* @soapy1
* @steffenvan


4.6.7 (2019-02-21)
==================

Bug fixes
^^^^^^^^^

* Skip scanning folders for contents during reversal of transactions.  Just ignore folders.  A bit messier, but a lot faster.  (#8266)
* Fix some logic in renaming trash files to fix permission errors  (#8300)
* Wrap pip subprocess calls in conda-env more cleanly and uniformly  (#8307)
* Revert conda prepending to PATH in cli main file on windows  (#8307)
* Simplify ``conda run`` code to use activation subprocess wrapper.  Fix a few conda tests to use ``conda run``.  (#8307)

Docs improvements
^^^^^^^^^^^^^^^^^

* Fixed duplicated "to" in managing envs section (#8298)
* Flesh out docs on activation  (#8314)
* Correct git syntax for adding a remote in dev docs  (#8316)
* Unpin Sphinx version in docs requirements  (#8317)

Contributors
^^^^^^^^^^^^

* @jjhelmus
* @MarckK
* @msarahan
* @rrigdon
* @samgd


4.6.6 (2019-02-18)
==================

Bug fixes
^^^^^^^^^

* Fix incorrect syntax prepending to PATH for conda CLI functionality  (#8295)
* Fix rename_tmp.bat operating on folders, leading to hung interactive dialogs.  Operate only on files.  (#8295)

Contributors
^^^^^^^^^^^^

* @mingwandroid
* @msarahan


4.6.5 (2019-02-15)
==================

Bug fixes
^^^^^^^^^

* Make super in resolve.py Python 2 friendly  (#8280)
* Support unicode paths better in activation scripts on Windows (#)
* Set PATH for conda.bat to include Conda's root prefix, so that libraries can be found when using conda when the root env is not activated  (#8287, #8292)
* Clean up warnings/errors about rsync and trash files  (#8290)

Contributors
^^^^^^^^^^^^

* @jjhelmus
* @mingwandroid
* @msarahan
* @rrigdon

4.6.4 (2019-02-13)
==================

Improvements
^^^^^^^^^^^^

* Allow configuring location of instrumentation records  (#7849)
* Prepend conda-env pip commands with env activation to fix library loading  (#8263)

Bug fixes
^^^^^^^^^

* Resolve #8176 SAT solver choice error handling  (#8248)
* Document ``pip_interop_enabled`` config parameter  (#8250)
* Ensure prefix temp files are inside prefix  (#8253)
* Ensure ``script_caller`` is bound before use  (#8254)
* Fix overzealous removal of folders after cleanup of failed post-link scripts  (#8259)
* Fix #8264: Allow 'int' datatype for values to non-sequence parameters  (#8268)

Deprecations/Breaking changes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Remove experimental ``featureless_minimization_disabled`` feature flag  (#8249)

Contributors
^^^^^^^^^^^^

* @davemasino
* @geremih
* @jjhelmus
* @kalefranz
* @msarahan
* @minrk
* @nehaljwani
* @prusse-martin
* @rrigdon
* @soapy1

4.6.3 (2019-02-07)
==================

Improvements
^^^^^^^^^^^^

* Implement ``-stack`` switch for powershell usage of conda (#8217)
* Enable system-wide initialization for conda shell support (#8219)
* Activate environments prior to running post-link scripts (#8229)
* Instrument more solve calls to prioritize future optimization efforts (#8231)
* print more env info when searching in envs (#8240)

Bug fixes
^^^^^^^^^

* Resolve #8178, fix conda pip interop assertion error with egg folders (#8184)
* Resolve #8157, fix token leakage in errors and config output (#8163)
* Resolve #8185, fix conda package filtering with embedded/vendored Python metadata (#8198)
* Resolve #8199, fix errors on .* in version specs that should have been specific to the ~= operator (#8208)
* Fix .bat scripts for handling paths on Windows with spaces (#8215)
* Fix powershell scripts for handling paths on Windows with spaces (#8222)
* Handle missing rename script more gracefully (especially when updating/installing conda itself) (#8212)

Contributors
^^^^^^^^^^^^

* @dhirschfeld
* @jjhelmus
* @kalefranz
* @msarahan
* @murrayreadccdc
* @nehaljwani
* @rrigdon
* @soapy1

4.6.2 (2019-01-29)
==================

Improvements
^^^^^^^^^^^^

* Documentation restructuring/improvements  (#8139, #8143)
* Rewrite rm_rf to use native system utilities and rename trash files  (#8134)

Bug fixes
^^^^^^^^^

* Fix UnavailableInvalidChannel errors when only noarch subdir is present  (#8154)
* Document, but disable the ``allow_conda_downgrades`` flag, pending re-examination of the warning, which was blocking conda operations after an upgrade-downgrade cycle across minor versions.  (#8160)
* Fix conda env export missing pip entries without use of pip interop enabled setting  (#8165)

Contributors
^^^^^^^^^^^^

* @jjhelmus
* @msarahan
* @nehaljwani
* @rrigdon


4.5.13 (2019-01-29)
===================

Improvements
^^^^^^^^^^^^

* Document the allow_conda_downgrades configuration parameter (#8034)
* Remove conda upgrade message (#8161)

Contributors
^^^^^^^^^^^^

* @msarahan
* @nehaljwani


4.6.1 (2019-01-21)
==================

Improvements
^^^^^^^^^^^^

* Optimizations in ``get_reduced_index`` (#8117, #8121, #8122)

Bug fixes
^^^^^^^^^

* Fix faulty onerror call for rm (#8053)
* Fix activate.bat to use more direct call to conda.bat (don't require conda init; fix non-interactive script) (#8113)


Contributors
^^^^^^^^^^^^

* @jjhelmus
* @msarahan
* @pv


4.6.0 (2019-01-15)
==================

New feature highlights
^^^^^^^^^^^^^^^^^^^^^^

* Resolve #7053 preview support for conda operability with pip; disabled by default (#7067, #7370, #7710, #8050)
* Conda initialize (#6518, #7388, #7629)
* Resolve #7194 add '--stack' flag to 'conda activate'; remove max_shlvl
  config (#7195, #7226, #7233)
* Resolve #7087 add non-conda-installed Python packages into PrefixData (#7067, #7370)
* Resolve #2682 add 'conda run' preview support (#7320, #7625)
* Resolve #626 conda wrapper for PowerShell (#7794, #7829)

Deprecations/Breaking changes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Resolve #6915 remove 'conda env attach' and 'conda env upload' (#6916)
* Resolve #7061 remove pkgs/pro from defaults (#7162)
* Resolve #7078 add deprecation warnings for 'conda.cli.activate',
  'conda.compat', and 'conda.install' (#7079)
* Resolve #7194 add '--stack' flag to 'conda activate'; remove max_shlvl
  config (#7195)
* Resolve #6979, #7086 remove Dist from majority of project (#7216, #7252)
* Fix #7362 remove --license from conda info and related code paths (#7386)
* Resolve #7309 deprecate 'conda info package_name' (#7310)
* Remove 'conda clean --source-cache' and defer to conda-build (#7731)
* Resolve #7724 move windows package cache and envs dirs back to .conda directory (#7725)
* Disallow env names with colons (#7801)

Improvements
^^^^^^^^^^^^

* Import speedups (#7122)
* --help cleanup (#7120)
* Fish autocompletion for conda env (#7101)
* Remove reference to 'system' channel (#7163)
* Add http error body to debug information (#7160)
* Warn creating env name with space is not supported (#7168)
* Support complete MatchSpec syntax in environment.yml files (#7178)
* Resolve #4274 add option to remove an existing environment with 'conda create' (#7133)
* Add ability for conda prompt customization via 'env_prompt' config param (#7047)
* Resolve #7063 add license and license_family to MatchSpec for 'conda search' (#7064)
* Resolve #7189 progress bar formatting improvement (#7191)
* Raise log level for errors to error (#7229)
* Add to conda.exports (#7217)
* Resolve #6845 add option -S / --satisfied-skip-solve to exit early for satisfied specs (#7291)
* Add NoBaseEnvironmentError and DirectoryNotACondaEnvironmentError (#7378)
* Replace menuinst subprocessing by ctypes win elevation (4.6.0a3) (#7426)
* Bump minimum requests version to stable, unbundled release (#7528)
* Resolve #7591 updates and improvements from namespace PR for 4.6 (#7599)
* Resolve #7592 compatibility shims (#7606)
* User-agent context refactor (#7630)
* Solver performance improvements with benchmarks in common.logic (#7676)
* Enable fuzzy-not-equal version constraint for pip interop (#7711)
* Add -d short option for --dry-run (#7719)
* Add --force-pkgs-dirs option to conda clean (#7719)
* Address #7709 ensure --update-deps unlocks specs from previous user requests (#7719)
* Add package timestamp information to output of 'conda search --info' (#7722)
* Resolve #7336 'conda search' tries "fuzzy match" before showing PackagesNotFound (#7722)
* Resolve #7656 strict channel priority via 'channel_priority' config option or --strict-channel-priority CLI flag (#7729)
* Performance improvement to cache __hash__ value on PackageRecord (#7715)
* Resolve #7764 change name of 'condacmd' dir to 'condabin'; use on all platforms (#7773)
* Resolve #7782 implement PEP-440 '~=' compatible release operator (#7783)
* Disable timestamp prioritization when not needed (#7894, #8012)
* Compile pyc files for noarch packages in batches (#8015)
* Disable per-file sha256 safety checks by default; add extra_safety_checks condarc option to enable them (#8017)
* Shorten retries for file removal on windows, where in-use files can't be removed (#8024)
* Expand env vars in ``custom_channels``, ``custom_multichannels``, ``default_channels``, ``migrated_custom_channels``, and ``whitelist_channels`` (#7826)
* Encode repodata to utf-8 while caching, to fix unicode characters in repodata (#7873)

Bug fixes
^^^^^^^^^

* Fix #7107 verify hangs when a package is corrupted (#7131)
* Fix #7145 progress bar uses stderr instead of stdout (#7146)
* Fix typo in conda.fish (#7152)
* Fix #2154 conda remove should complain if requested removals don't exist (#7135)
* Fix #7094 exit early for --dry-run with explicit and clone (#7096)
* Fix activation script sort order (#7176)
* Fix #7109 incorrect chown with sudo (#7180)
* Fix #7210 add suppressed --mkdir back to 'conda create' (fix for 4.6.0a1) (#7211)
* Fix #5681 conda env create / update when --file does not exist (#7385)
* Resolve #7375 enable conda config --set update_modifier (#7377)
* Fix #5885 improve conda env error messages and add extra tests (#7395)
* Msys2 path conversion (#7389)
* Fix autocompletion in fish (#7575)
* Fix #3982 following 4.4 activation refactor (#7607)
* Fix #7242 configuration load error message (#7243)
* Fix conda env compatibility with pip 18 (#7612)
* Fix #7184 remove conflicting specs to find solution to user's active request (#7719)
* Fix #7706 add condacmd dir to cmd.exe path on first activation (#7735)
* Fix #7761 spec handling errors in 4.6.0b0 (#7780)
* Fix #7770 'conda list regex' only applies regex to package name (#7784)
* Fix #8076 load metadata from index to resolve inconsistent envs (#8083)

Non-user-facing changes
^^^^^^^^^^^^^^^^^^^^^^^

* Resolve #6595 use OO inheritance in activate.py (#7049)
* Resolve #7220 pep8 project renamed to pycodestyle (#7221)
* Proxy test routine (#7308)
* Add .mailmap and .cla-signers (#7361)
* Add copyright headers (#7367)
* Rename common.platform to common.os and split among windows, linux, and unix utils (#7396)
* Fix windows test failures when symlink not available (#7369)
* Test building conda using conda-build (#7251)
* Solver test metadata updates (#7664)
* Explicitly add Mapping, Sequence to common.compat (#7677)
* Add debug messages to communicate solver stages (#7803)
* Add undocumented sat_solver config parameter (#7811)

Preview Releases
^^^^^^^^^^^^^^^^

* 4.6.0a1 at d5bec21d1f64c3bc66c2999cfc690681e9c46177 on 2018-04-20
* 4.6.0a2 at c467517ca652371ebc4224f0d49315b7ec225108 on 2018-05-01
* 4.6.0b0 at 21a24f02b2687d0895de04664a4ec23ccc75c33a on 2018-09-07
* 4.6.0b1 at 1471f043eed980d62f46944e223f0add6a9a790b on 2018-10-22
* 4.6.0rc1 at 64bde065f8343276f168d2034201115dff7c5753 on 2018-12-31

Contributors
^^^^^^^^^^^^

* @cgranade
* @fabioz
* @geremih
* @goanpeca
* @jesse-
* @jjhelmus
* @kalefranz
* @makbigc
* @mandeep
* @mbargull
* @msarahan
* @nehaljwani
* @ohadravid
* @teake

4.5.12 (2018-12-10)
===================

Improvements
^^^^^^^^^^^^

* Backport 'allow_conda_downgrade' configuration parameter, default is False (#7998)
* Speed up verification by disabling per-file sha256 checks (#8017)
* Indicate Python 3.7 support in setup.py file (#8018)
* Speed up solver by reduce the size of reduced index (#8016)
* Speed up solver by skipping timestamp minimization when not needed (#8012)
* Compile pyc files more efficiently, will speed up install of noarch packages (#8025)
* Avoid waiting for removal of files on Windows when possible (#8024)

Bug fixes
^^^^^^^^^

* Update integration tests for removal of 'features' key (#7726)
* Fix conda.bat return code (#7944)
* Ensure channel name is not NoneType (#8021)

Contributors
^^^^^^^^^^^^

* @debionne
* @jjhelmus
* @kalefranz
* @msarahan
* @nehaljwani


4.5.11 (2018-08-21)
===================

Improvements
^^^^^^^^^^^^

* Resolve #7672 compatibility with ruamel.yaml 0.15.54 (#7675)

Contributors
^^^^^^^^^^^^

* @CJ-Wright
* @mbargull


4.5.10 (2018-08-13)
===================

Bug fixes
^^^^^^^^^

* Fix conda env compatibility with pip 18 (#7627)
* Fix py37 compat 4.5.x (#7641)
* Fix #7451 don't print name, version, and size if unknown (#7648)
* Replace glob with fnmatch in PrefixData (#7645)

Contributors
^^^^^^^^^^^^

* @jesse-
* @nehaljwani


4.5.9 (2018-07-30)
==================

Improvements
^^^^^^^^^^^^

* Resolve #7522 prevent conda from scheduling downgrades (#7598)
* Allow skipping feature maximization in resolver (#7601)

Bug fixes
^^^^^^^^^

* Fix #7559 symlink stat in localfs adapter (#7561)
* Fix #7486 activate with no PATH set (#7562)
* Resolve #7522 prevent conda from scheduling downgrades (#7598)

Contributors
^^^^^^^^^^^^

* @kalefranz
* @loriab


4.5.8 (2018-07-10)
==================

Bug fixes
^^^^^^^^^

* Fix #7524 should_bypass_proxies for requests 2.13.0 and earlier (#7525)

Contributors
^^^^^^^^^^^^

* @kalefranz


4.5.7 (2018-07-09)
==================

Improvements
^^^^^^^^^^^^

* Resolve #7423 add upgrade error for unsupported repodata_version (#7415)
* Raise CondaUpgradeError for conda version downgrades on environments (#7517)

Bug fixes
^^^^^^^^^

* Fix #7505 temp directory for UnlinkLinkTransaction should be in target prefix (#7516)
* Fix #7506 requests monkeypatch fallback for old requests versions (#7515)

Contributors
^^^^^^^^^^^^

* @kalefranz
* @nehaljwani


4.5.6 (2018-07-06)
==================

Bug fixes
^^^^^^^^^

* Resolve #7473 py37 support (#7499)
* Fix #7494 History spec parsing edge cases (#7500)
* Fix requests 2.19 incompatibility with NO_PROXY env var (#7498)
* Resolve #7372 disable http error uploads and CI cleanup (#7498, #7501)

Contributors
^^^^^^^^^^^^

* @kalefranz


4.5.5 (2018-06-29)
==================

Bug fixes
^^^^^^^^^

* Fix #7165 conda version check should be restricted to channel conda is from (#7289, #7303)
* Fix #7341 ValueError n cannot be negative (#7360)
* Fix #6691 fix history file parsing containing comma-joined version specs (#7418)
* Fix msys2 path conversion (#7471)

Contributors
^^^^^^^^^^^^

* @goanpeca
* @kalefranz
* @mingwandroid
* @mbargull


4.5.4 (2018-05-14)
==================

Improvements
^^^^^^^^^^^^

* Resolve #7189 progress bar improvement (#7191 via #7274)

Bug fixes
^^^^^^^^^

* Fix twofold tarball extraction, improve progress update (#7275)
* Fix #7253 always respect copy LinkType (#7269)

Contributors
^^^^^^^^^^^^

* @jakirkham
* @kalefranz
* @mbargull


4.5.3 (2018-05-07)
==================

Bug fixes
^^^^^^^^^

* Fix #7240 conda's configuration context is not initialized in conda.exports (#7244)


4.5.2 (2018-04-27)
==================

Bug fixes
^^^^^^^^^

* Fix #7107 verify hangs when a package is corrupted (#7223)
* Fix #7094 exit early for --dry-run with explicit and clone (#7224)
* Fix activation/deactivation script sort order (#7225)


4.5.1 (2018-04-13)
==================

Improvements
^^^^^^^^^^^^

* Resolve #7075 add anaconda.org search message to PackagesNotFoundError (#7076)
* Add CondaError details to auto-upload reports (#7060)

Bug fixes
^^^^^^^^^

* Fix #6703,#6981 index out of bound when running deactivate on fish shell (#6993)
* Properly close over $_CONDA_EXE variable (#7004)
* Fix condarc map parsing with comments (#7021)
* Fix #6919 csh prompt (#7041)
* Add _file_created attribute (#7054)
* Fix handling of non-ascii characters in custom_multichannels (#7050)
* Fix #6877 handle non-zero return in CSH (#7042)
* Fix #7040 update tqdm to version 4.22.0 (#7157)


4.5.0 (2018-03-20)
==================

New feature highlights
^^^^^^^^^^^^^^^^^^^^^^

* A new flag, '--envs', has been added to 'conda search'. In this mode,
  'conda search' will look for the package query in existing conda environments
  on your system. If ran as UID 0 (i.e. root) on unix systems or as an
  Administrator user on Windows, all known conda environments for all users
  on the system will be searched.  For example, 'conda search --envs openssl'
  will show the openssl version and environment location for all
  conda-installed openssl packages.

Deprecations/Breaking changes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Resolve #6886 transition defaults from repo.continuum.io to repo.anaconda.com (#6887)
* Resolve #6192 deprecate 'conda help' in favor of --help CLI flag (#6918)
* Resolve #6894 add http errors to auto-uploaded error reports (#6895)

Improvements
^^^^^^^^^^^^

* Resolve #6791 conda search --envs (#6794)
* preserve exit status in fish shell (#6760)
* Resolve #6810 add CONDA_EXE environment variable to activate (#6923)
* Resolve #6695 outdated conda warning respects --quiet flag (#6935)
* Add instructions to activate default environment (#6944)

API
^^^

* Resolve #5610 add PrefixData, SubdirData, and PackageCacheData to conda/api.py (#6922)

Bug fixes
^^^^^^^^^

* Channel matchspec fixes (#6893)
* Fix #6930 add missing return statement to S3Adapter (#6931)
* Fix #5802, #6736 enforce disallowed_packages configuration parameter (#6932)
* Fix #6860 infinite recursion in resolve.py for empty track_features (#6928)
* set encoding for PY2 stdout/stderr (#6951)
* Fix #6821 non-deterministic behavior from MatchSpec merge clobbering (#6956)
* Fix #6904 logic errors in prefix graph data structure (#6929)

Non-user-facing changes
^^^^^^^^^^^^^^^^^^^^^^^

* Fix several lgtm.com flags (#6757, #6883)
* Cleanups and refactors for conda 4.5 (#6889)
* Unify location of record types in conda/models/records.py (#6924)
* Resolve #6952 memoize url search in package cache loading (#6957)


4.4.11 (2018-02-23)
===================

Improvements
^^^^^^^^^^^^

* Resolve #6582 swallow_broken_pipe context manager and Spinner refactor (#6616)
* Resolve #6882 document max_shlvl (#6892)
* Resolve #6733 make empty env vars sequence-safe for sequence parameters (#6741)
* Resolve #6900 don't record conda skeleton environments in environments.txt (#6908)

Bug fixes
^^^^^^^^^

* Fix potential error in ensure_pad(); add more tests (#6817)
* Fix #6840 handle error return values in conda.sh (#6850)
* Use conda.gateways.disk for misc.py imports (#6870)
* Fix #6672 don't update conda during conda-env operations (#6773)
* Fix #6811 don't attempt copy/remove fallback for rename failures (#6867)
* Fix #6667 aliased posix commands (#6669)
* Fix #6816 fish environment autocomplete (#6885)
* Fix #6880 build_number comparison not functional in match_spec (#6881)
* Fix #6910 sort key prioritizes build string over build number (#6911)
* Fix #6914, #6691 conda can fail to update packages even though newer versions exist (#6921)
* Fix #6899 handle Unicode output in activate commands (#6909)

4.4.10 (2018-02-09)
===================

Bug fixes
^^^^^^^^^

* Fix #6837 require at least futures 3.0.0 (#6855)
* Fix #6852 ensure temporary path is writable (#6856)
* Fix #6833 improve feature mismatch metric (via 4.3.34 #6853)


4.4.9 (2018-02-06)
==================

Improvements
^^^^^^^^^^^^

* Resolve #6632 display package removal plan when deleting an env (#6801)

Bug fixes
^^^^^^^^^

* Fix #6531 don't drop credentials for conda-build workaround (#6798)
* Fix external command execution issue (#6789)
* Fix #5792 conda env export error common in path (#6795)
* Fix #6390 add CorruptedEnvironmentError (#6778)
* Fix #5884 allow --insecure CLI flag without contradicting meaning of ssl_verify (#6782)
* Fix MatchSpec.match() accepting dict (#6808)
* Fix broken Anaconda Prompt for users with spaces in paths (#6825)
* JSONDecodeError was added in Python 3.5 (#6848)
* Fix #6796 update PATH/prompt on reactivate (#6828)
* Fix #6401 non-ascii characters on windows using expanduser (#6847)
* Fix #6824 import installers before invoking any (#6849)


4.4.8 (2018-01-25)
==================

Improvements
^^^^^^^^^^^^

* Allow falsey values for default_python to avoid pinning Python (#6682)
* Resolve #6700 add message for no space left on device (#6709)
* Make variable 'sourced' local for posix shells (#6726)
* Add column headers to conda list results (#5726)

Bug fixes
^^^^^^^^^

* Fix #6713 allow parenthesis in prefix path for conda.bat (#6722)
* Fix #6684 --force message (#6723)
* Fix #6693 KeyError with '--update-deps' (#6694)
* Fix aggressive_update_packages availability (#6727)
* Fix #6745 don't truncate channel priority map in conda installer (#6746)
* Add workaround for system Python usage by lsb_release (#6769)
* Fix #6624 can't start new thread (#6653)
* Fix #6628 'conda install --rev' in conda 4.4 (#6724)
* Fix #6707 FileNotFoundError when extracting tarball (#6708)
* Fix #6704 unexpected token in conda.bat (#6710)
* Fix #6208 return for no pip in environment (#6784)
* Fix #6457 env var cleanup (#6790)
* Fix #6645 escape paths for argparse help (#6779)
* Fix #6739 handle unicode in environment variables for py2 activate (#6777)
* Fix #6618 RepresenterError with 'conda config --set' (#6619)
* Fix #6699 suppress memory error upload reports (#6776)
* Fix #6770 CRLF for cmd.exe (#6775)
* Fix #6514 add message for case-insensitive filesystem errors (#6764)
* Fix #6537 AttributeError value for url not set (#6754)
* Fix #6748 only warn if unable to register environment due to EACCES (#6752)


4.4.7 (2018-01-08)
==================

Improvements
^^^^^^^^^^^^

* Resolve #6650 add upgrade message for unicode errors in Python 2 (#6651)

Bug fixes
^^^^^^^^^

* Fix #6643 difference between ``==`` and ``exact_match_`` (#6647)
* Fix #6620 KeyError(u'CONDA_PREFIX',) (#6652)
* Fix #6661 remove env from environments.txt (#6662)
* Fix #6629 'conda update --name' AssertionError (#6656)
* Fix #6630 repodata AssertionError (#6657)
* Fix #6626 add setuptools as constrained dependency (#6654)
* Fix #6659 conda list explicit should be dependency sorted (#6671)
* Fix #6665 KeyError for channel '<unknown>' (#6668, #6673)
* Fix #6627 AttributeError on 'conda activate' (#6655)


4.4.6 (2017-12-31)
==================

Bug fixes
^^^^^^^^^

* Fix #6612 do not assume Anaconda Python on Windows nor Library\bin hack (#6615)
* Recipe test improvements and associated bug fixes (#6614)


4.4.5 (2017-12-29)
==================

Bug fixes
^^^^^^^^^

* Fix #6577, #6580 single quote in PS1 (#6585)
* Fix #6584 os.getcwd() FileNotFound (#6589)
* Fix #6592 deactivate command order (#6602)
* Fix #6579 Python not recognized as command (#6588)
* Fix #6572 cached repodata PermissionsError (#6573)
* Change instances of 'root' to 'base' (#6598)
* Fix #6607 use subprocess rather than execv for conda command extensions (#6609)
* Fix #6581 git-bash activation (#6587)
* Fix #6599 space in path to base prefix (#6608)


4.4.4 (2017-12-24)
==================

Improvements
^^^^^^^^^^^^

* Add ``SUDO_`` env vars to info reports (#6563)
* Add additional information to the #6546 exception (#6551)

Bug fixes
^^^^^^^^^

* Fix #6548 'conda update' installs packages not in prefix #6550
* Fix #6546 update after creating an empty env (#6568)
* Fix #6557 conda list FileNotFoundError (#6558)
* Fix #6554 package cache FileNotFoundError (#6555)
* Fix #6529 yaml parse error (#6560)
* Fix #6562 repodata_record.json permissions error stack trace (#6564)
* Fix #6520 --use-local flag (#6526)

4.4.3 (2017-12-22)
==================

Improvements
^^^^^^^^^^^^

* Adjust error report message (#6534)

Bug fixes
^^^^^^^^^

* Fix #6530 package cache JsonDecodeError / ValueError (#6533)
* Fix #6538 BrokenPipeError (#6540)
* Fix #6532 remove anaconda metapackage hack (#6539)
* Fix #6536 'conda env export' for old versions of pip (#6535)
* Fix #6541 py2 and unicode in environments.txt (#6542)

Non-user-facing changes
^^^^^^^^^^^^^^^^^^^^^^^

* Regression tests for #6512 (#6515)


4.4.2 (2017-12-22)
==================

Deprecations/Breaking changes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Resolve #6523 don't prune with --update-all (#6524)

Bug fixes
^^^^^^^^^

* Fix #6508 environments.txt permissions error stack trace (#6511)
* Fix #6522 error message formatted incorrectly (#6525)
* Fix #6516 hold channels over from get_index to install_actions (#6517)


4.4.1 (2017-12-21)
==================

Bug fixes
^^^^^^^^^

* Fix #6512 reactivate does not accept arguments (#6513)


4.4.0 (2017-12-20)
==================

Recommended change to enable conda in your shell
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

With the release of conda 4.4, we recommend a change to how the `conda` command is made available to your shell environment. All the old methods still work as before, but you'll need the new method to enable the new `conda activate` and `conda deactivate` commands.

For the "Anaconda Prompt" on Windows, there is no change.

For Bourne shell derivatives (bash, zsh, dash, etc.), you likely currently have a line similar to::

    export PATH="/opt/conda/bin:$PATH"

in your `~/.bashrc` file (or `~/.bash_profile` file on macOS).  The effect of this line is that your base environment is put on PATH, but without actually *activating* that environment. (In 4.4 we've renamed the 'root' environment to the 'base' environment.) With conda 4.4, we recommend removing the line where the `PATH` environment variable is modified, and replacing it with::

    . /opt/conda/etc/profile.d/conda.sh
    conda activate base

In the above, it's assumed that `/opt/conda` is the location where you installed miniconda or Anaconda.  It may also be something like `~/Anaconda3` or `~/miniconda2`.

For system-wide conda installs, to make the `conda` command available to all users, rather than manipulating individual `~/.bashrc` (or `~/.bash_profile`) files for each user, just execute once::

    $ sudo ln -s /opt/conda/etc/profile.d/conda.sh /etc/profile.d/conda.sh

This will make the `conda` command itself available to all users, but conda's base (root) environment will *not* be activated by default.  Users will still need to run `conda activate base` to put the base environment on PATH and gain access to the executables in the base environment.

After updating to conda 4.4, we also recommend pinning conda to a specific channel.  For example, executing the command::

    $ conda config --system --add pinned_packages conda-canary::conda

will make sure that whenever conda is installed or changed in an environment, the source of the package is always being pulled from the `conda-canary` channel.  This will be useful for people who use `conda-forge`, to prevent conda from flipping back and forth between 4.3 and 4.4.


New feature highlights
^^^^^^^^^^^^^^^^^^^^^^

* **conda activate**: The logic and mechanisms underlying environment activation have been reworked. With conda 4.4, `conda activate` and `conda deactivate` are now the preferred commands for activating and deactivating environments. You'll find they are much more snappy than the `source activate` and `source deactivate` commands from previous conda versions. The `conda activate` command also has advantages of (1) being universal across all OSes, shells, and platforms, and (2) not having path collisions with scripts from other packages like Python virtualenv's activate script.


* **constrained, optional dependencies**: Conda now allows a package to constrain versions of other packages installed alongside it, even if those constrained packages are not themselves hard dependencies for that package. In other words, it lets a package specify that, if another package ends up being installed into an environment, it must at least conform to a certain version specification. In effect, constrained dependencies are a type of "reverse" dependency. It gives a tool to a parent package to exclude other packages from an environment that might otherwise want to depend on it.

  Constrained optional dependencies are supported starting with conda-build 3.0 (via `conda/conda-build#2001 <https://github.com/conda/conda-build/pull/2001>`_). A new `run_constrained` keyword, which takes a list of package specs similar to the `run` keyword, is recognized under the `requirements` section of `meta.yaml`. For backward compatibility with versions of conda older than 4.4, a requirement may be listed in both the `run` and the `run_constrained` section. In that case older versions of conda will see the package as a hard dependency, while conda 4.4 will understand that the package is meant to be optional.

  Optional, constrained dependencies end up in `repodata.json` under a `constrains` keyword, parallel to the `depends` keyword for a package's hard dependencies.


* **enhanced package query language**: Conda has a built-in query language for searching for and matching packages, what we often refer to as `MatchSpec`. The MatchSpec is what users input on the command line when they specify packages for `create`, `install`, `update`, and `remove` operations. With this release, MatchSpec (rather than a regex) becomes the default input for `conda search`. We have also substantially enhanced our MatchSpec query language.

  For example::

      conda install conda-forge::Python

  is now a valid command, which specifies that regardless of the active list of channel priorities, the Python package itself should come from the `conda-forge` channel. As before, the difference between `Python=3.5` and `Python==3.5` is that the first contains a "*fuzzy*" version while the second contains an *exact* version. The fuzzy spec will match all Python packages with versions `>=3.5` and `<3.6`. The exact spec will match only Python packages with version `3.5`, `3.5.0`, `3.5.0.0`, etc. The canonical string form for a MatchSpec is thus::

      (channel::)name(version(build_string))

  which should feel natural to experienced conda users. Specifications however are often necessarily more complicated than this simple form can support, and for these situations we've extended the specification to include an optional square bracket `[]` component containing comma-separated key-value pairs to allow matching on most any field contained in a package's metadata. Take, for example::

      conda search 'conda-forge/linux-64::*[md5=e42a03f799131d5af4196ce31a1084a7]' --info

  which results in information for the single package::

      cytoolz 0.8.2 py35_0
      --------------------
      file name   : cytoolz-0.8.2-py35_0.tar.bz2
      name        : cytoolz
      version     : 0.8.2
      build string: py35_0
      build number: 0
      size        : 1.1 MB
      arch        : x86_64
      platform    : Platform.linux
      license     : BSD 3-Clause
      subdir      : linux-64
      url         : https://conda.anaconda.org/conda-forge/linux-64/cytoolz-0.8.2-py35_0.tar.bz2
      md5         : e42a03f799131d5af4196ce31a1084a7
      dependencies:
        - Python 3.5*
        - toolz >=0.8.0

  The square bracket notation can also be used for any field that we match on outside the package name, and will override information given in the "simple form" position. To give a contrived example, `Python==3.5[version='>=2.7,<2.8']` will match `2.7.*` versions and not `3.5`.


* **environments track user-requested state**: Building on our enhanced MatchSpec query language, conda environments now also track and differentiate (a) packages added to an environment because of an explicit user request from (b) packages brought into an environment to satisfy dependencies. For example, executing::

      conda install conda-forge::scikit-learn

  will confine all future changes to the scikit-learn package in the environment to the conda-forge channel, until the spec is changed again. A subsequent command `conda install scikit-learn=0.18` would drop the `conda-forge` channel restriction from the package. And in this case, scikit-learn is the only user-defined spec, so the solver chooses dependencies from all configured channels and all available versions.


* **errors posted to core maintainers**: In previous versions of conda, unexpected errors resulted in a request for users to consider posting the error as a new issue on conda's github issue tracker. In conda 4.4, we've implemented a system for users to opt-in to sending that same error report via an HTTP POST request directly to the core maintainers.

  When an unexpected error is encountered, users are prompted with the error report followed by a `[y/N]` input. Users can elect to send the report, with 'no' being the default response. Users can also permanently opt-in or opt-out, thereby skipping the prompt altogether, using the boolean `report_errors` configuration parameter.


* **various UI improvements**: To push through some of the big leaps with transactions in conda 4.3, we accepted some regressions on progress bars and other user interface features. All of those indicators of progress, and more, have been brought back and further improved.


* **aggressive updates**: Conda now supports an `aggressive_update_packages` configuration parameter that holds a sequence of MatchSpec strings, in addition to the `pinned_packages` configuration parameter. Currently, the default value contains the packages `ca-certificates`, `certifi`, and `openssl`. When manipulating configuration with the `conda config` command, use of the `--system` and `--env` flags will be especially helpful here. For example::

      conda config --add aggressive_update_packages defaults::pyopenssl --system

  would ensure that, system-wide, solves on all environments enforce using the latest version of `pyopenssl` from the `defaults` channel.

  ```conda config --add pinned_packages Python=2.7 --env```

  would lock all solves for the current active environment to Python versions matching `2.7.*`.


* **other configuration improvements**: In addition to `conda config --describe`, which shows detailed descriptions and default values for all available configuration parameters, we have a new `conda config --write-default` command. This new command simply writes the contents of `conda config --describe` to a condarc file, which is a great starter template. Without additional arguments, the command will write to the `.condarc` file in the user's home directory. The command also works with the `--system`, `--env`, and `--file` flags to write the contents to alternate locations.

  Conda exposes a tremendous amount of flexibility via configuration. For more information, `The Conda Configuration Engine for Power Users <https://www.continuum.io/blog/developer-blog/conda-configuration-engine-power-users>`_ blog post is a good resource.


Deprecations/Breaking changes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* The conda 'root' environment is now generally referred to as the 'base' environment
* Conda 4.4 now warns when available information about per-path sha256 sums and file sizes
  do not match the recorded information.  The warning is scheduled to be an error in conda 4.5.
  Behavior is configurable via the `safety_checks` configuration parameter.
* Remove support for with_features_depends (#5191)
* Resolve #5468 remove --alt-hint from CLI API (#5469)
* Resolve #5834 change default value of 'allow_softlinks' from True to False (#5835)
* Resolve #5842 add deprecation warnings for 'conda env upload' and 'conda env attach' (#5843)

API
^^^

* Add Solver from conda.core.solver with three methods to conda.api (4.4.0rc1) (#5838)

Improvements
^^^^^^^^^^^^

* Constrained, optional dependencies (#4982)
* Conda shell function (#5044, #5141, #5162, #5169, #5182, #5210, #5482)
* Resolve #5160 conda xontrib plugin (#5157)
* Resolve #1543 add support and tests for --no-deps and --only-deps (#5265)
* Resolve #988 allow channel name to be part of the package name spec (#5365, #5791)
* Resolve #5530 add ability for users to choose to post unexpected errors to core maintainers (#5531, #5571, #5585)
* Solver, UI, History, and Other (#5546, #5583, #5740)
* Improve 'conda search' to leverage new MatchSpec query language (#5597)
* Filter out unwritable package caches from conda clean command (#4620)
* Envs_manager, requested spec history, declarative solve, and private env tests (#4676, #5114, #5094, #5145, #5492)
* Make Python entry point format match pip entry points (#5010)
* Resolve #5113 clean up CLI imports to improve process startup time (#4799)
* Resolve #5121 add features/track_features support for MatchSpec (#5054)
* Resolve #4671 hold verify backoff count in transaction context (#5122)
* Resolve #5078 record package metadata after tarball extraction (#5148)
* Resolve #3580 support stacking environments (#5159)
* Resolve #3763, #4378 allow pip requirements.txt syntax in environment files (#3969)
* Resolve #5147 add 'config files' to conda info (#5269)
* Use --format=json to parse list of pip packages (#5205)
* Resolve #1427 remove startswith '.' environment name constraint (#5284)
* Link packages from extracted tarballs when tarball is gone (#5289)
* Resolve #2511 accept config information from stdin (#5309)
* Resolve #4302 add ability to set map parameters with conda config (#5310)
* Resolve #5256 enable conda config --get for all primitive parameters (#5312)
* Resolve #1992 add short flag -C for --use-index-cache (#5314)
* Resolve #2173 add --quiet option to conda clean (#5313)
* Resolve #5358 conda should exec to subcommands, not subprocess (#5359)
* Resolve #5411 add 'conda config --write-default' (#5412)
* Resolve #5081 make pinned packages optional dependencies (#5414)
* Resolve #5430 eliminate current deprecation warnings (#5422)
* Resolve #5470 make stdout/stderr capture in python_api customizable (#5471)
* Logging simplifications/improvements (#5547, #5578)
* Update license information (#5568)
* Enable threadpool use for repodata collection by default (#5546, #5587)
* Conda info now raises PackagesNotFoundError (#5655)
* Index building optimizations (#5776)
* Fix #5811 change safety_checks default to 'warn' for conda 4.4 (4.4.0rc1) (#5824)
* Add constrained dependencies to conda's own recipe (4.4.0rc1) (#5823)
* Clean up parser imports (4.4.0rc2) (#5844)
* Resolve #5983 add --download-only flag to create, install, and update (4.4.0rc2) (#5988)
* Add ca-certificates and certifi to aggressive_update_packages default (4.4.0rc2) (#5994)
* Use environments.txt to list all known environments (4.4.0rc2) (#6313)
* Resolve #5417 ensure unlink order is correctly sorted (4.4.0) (#6364)
* Resolve #5370 index is only prefix and cache in --offline mode (4.4.0) (#6371)
* Reduce redundant sys call during file copying (4.4.0rc3) (#6421)
* Enable aggressive_update_packages (4.4.0rc3) (#6392)
* Default conda.sh to dash if otherwise can't detect (4.4.0rc3) (#6414)
* Canonicalize package names when comparing with pip (4.4.0rc3) (#6438)
* Add target prefix override configuration parameter (4.4.0rc3) (#6413)
* Resolve #6194 warn when conda is outdated (4.4.0rc3) (#6370)
* Add information to displayed error report (4.4.0rc3) (#6437)
* Csh wrapper (4.4.0) (#6463)
* Resolve #5158 --override-channels (4.4.0) (#6467)
* Fish update for conda 4.4 (4.4.0) (#6475, #6502)
* Skip an unnecessary environments.txt rewrite (4.4.0) (#6495)

Bug fixes
^^^^^^^^^

* Fix some conda-build compatibility issues (#5089)
* Resolve #5123 export toposort (#5124)
* Fix #5132 signal handler can only be used in main thread (#5133)
* Fix orphaned --clobber parser arg (#5188)
* Fix #3814 don't remove directory that's not a conda environment (#5204)
* Fix #4468 ``_license`` stack trace (#5206)
* Fix #4987 conda update --all no longer displays full list of packages (#5228)
* Fix #3489 don't error on remove --all if environment doesn't exist (#5231)
* Fix #1509 bash doesn't need full path for pre/post link/unlink scripts on unix (#5252)
* Fix #462 add regression test (#5286)
* Fix #5288 confirmation prompt doesn't accept no (#5291)
* Fix #1713 'conda package -w' is case dependent on Windows (#5308)
* Fix #5371 try falling back to pip's vendored requests if no requests available (#5372)
* Fix #5356 skip root logger configuration (#5380)
* Fix #5466 scrambled URL of non-alias channel with token (#5467)
* Fix #5444 environment.yml file not found (#5475)
* Fix #3200 use proper unbound checks in bash code and test (#5476)
* Invalidate PrefixData cache on rm_rf for conda-build (#5491, #5499)
* Fix exception when generating JSON output (#5628)
* Fix target prefix determination (#5642)
* Use proxy to avoid segfaults (#5716)
* Fix #5790 incorrect activation message (4.4.0rc1) (#5820)
* Fix #5808 assertion error when loading package cache (4.4.0rc1) (#5815)
* Fix #5809 ``_pip_install_via_requirements`` got an unexpected keyword argument 'prune' (4.4.0rc1) (#5814)
* Fix #5811 change safety_checks default to 'warn' for conda 4.4 (4.4.0rc1) (#5824)
* Fix #5825 --json output format (4.4.0rc1) (#5831)
* Fix force_reinstall for case when packages aren't actually installed (4.4.0rc1) (#5836)
* Fix #5680 empty pip subsection error in environment.yml (4.4.0rc2) (#6275)
* Fix #5852 bad tokens from history crash conda installs (4.4.0rc2) (#6076)
* Fix #5827 no error message on invalid command (4.4.0rc2) (#6352)
* Fix exception handler for 'conda activate' (4.4.0rc2) (#6365)
* Fix #6173 double prompt immediately after conda 4.4 upgrade (4.4.0rc2) (#6351)
* Fix #6181 keep existing pythons pinned to minor version (4.4.0rc2) (#6363)
* Fix #6201 incorrect subdir shown for conda search when package not found (4.4.0rc2) (#6367)
* Fix #6045 help message and zsh shift (4.4.0rc3) (#6368)
* Fix noarch Python package resintall (4.4.0rc3) (#6394)
* Fix #6366 shell activation message (4.4.0rc3) (#6369)
* Fix #6429 AttributeError on 'conda remove' (4.4.0rc3) (#6434)
* Fix #6449 problems with 'conda info --envs' (#6451)
* Add debug exception for #6430 (4.4.0rc3) (#6435)
* Fix #6441 NotImplementedError on 'conda list' (4.4.0rc3) (#6442)
* Fix #6445 scale back directory activation in PWD (4.4.0rc3) (#6447)
* Fix #6283 no-deps for conda update case (4.4.0rc3) (#6448)
* Fix #6419 set PS1 in Python code (4.4.0rc3) (#6446)
* Fix #6466 sp_dir doesn't exist (#6470)
* Fix #6350 --update-all removes too many packages (4.4.0) (#6491)
* Fix #6057 unlink-link order for Python noarch packages on windows 4.4.x (4.4.0) (#6494)

Non-user-facing changes
^^^^^^^^^^^^^^^^^^^^^^^

* Eliminate index modification in Resolve init (#4333)
* New MatchSpec implementation (#4158, #5517)
* Update conda.recipe for 4.4 (#5086)
* Resolve #5118 organization and cleanup for 4.4 release (#5115)
* Remove unused disk space check instructions (#5167)
* Localfs adapter tests (#5181)
* Extra config command tests (#5185)
* Add coverage for confirm (#5203)
* Clean up FileNotFoundError and DirectoryNotFoundError (#5237)
* Add assertion that a path only has a single hard link before rewriting prefixes (#5305)
* Remove pycrypto as requirement on windows (#5326)
* Import cleanup, dead code removal, coverage improvements, and other
  housekeeping (#5472, #5474, #5480)
* Rename CondaFileNotFoundError to PathNotFoundError (#5521)
* Work toward repodata API (#5267)
* Rename PackageNotFoundError to PackagesNotFoundError and Fix message formatting (#5602)
* Update conda 4.4 bld.bat windows recipe (#5573)
* Remove last remnant of CondaEnvRuntimeError (#5643)
* Fix typo (4.4.0rc2) (#6043)
* Replace Travis-CI with CircleCI (4.4.0rc2) (#6345)
* Key-value features (#5645); reverted in 4.4.0rc2 (#6347, #6492)
* Resolve #6431 always add env_vars to info_dict (4.4.0rc3) (#6436)
* Move shell inside conda directory (4.4.0) (#6479)
* Remove dead code (4.4.0) (#6489)


4.3.34 (2018-02-09)
===================

Bug fixes
^^^^^^^^^

* Fix #6833 improve feature mismatch metric (#6853)


4.3.33 (2018-01-24)
===================

Bug fixes
^^^^^^^^^

* Fix #6718 broken 'conda install --rev' (#6719)
* Fix #6765 adjust the feature score assigned to packages not installed (#6766)


4.3.32 (2018-01-10)
===================

Improvements
^^^^^^^^^^^^

* Resolve #6711 fall back to copy/unlink for EINVAL, EXDEV rename failures (#6712)

Bug fixes
^^^^^^^^^

* Fix #6057 unlink-link order for Python noarch packages on windows (#6277)
* Fix #6509 custom_channels incorrect in 'conda config --show' (#6510)


4.3.31 (2017-12-15)
===================

Improvements
^^^^^^^^^^^^

* Add delete_trash to conda_env create (#6299)

Bug fixes
^^^^^^^^^

* Fix #6023 assertion error for temp file (#6154)
* Fix #6220 --no-builds flag for 'conda env export' (#6221)
* Fix #6271 timestamp prioritization results in undesirable race-condition (#6279)

Non-user-facing changes
^^^^^^^^^^^^^^^^^^^^^^^

* Fix two failing integration tests after anaconda.org API change (#6182)
* Resolve #6243 mark root as not writable when sys.prefix is not a conda environment (#6274)
* Add timing instrumentation (#6458)


4.3.30 (2017-10-17)
===================

Improvements
^^^^^^^^^^^^

* Address #6056 add additional proxy variables to 'conda info --all' (#6083)

Bug fixes
^^^^^^^^^

* Address #6164 move add_defaults_to_specs after augment_specs (#6172)
* Fix #6057 add additional detail for message 'cannot link source that does not exist' (#6082)
* Fix #6084 setting default_channels from CLI raises NotImplementedError (#6085)


4.3.29 (2017-10-09)
===================

Bug fixes
^^^^^^^^^

* Fix #6096 coerce to millisecond timestamps (#6131)


4.3.28 (2017-10-06)
===================


Bug fixes
^^^^^^^^^

* Fix #5854 remove imports of pkg_resources (#5991)
* Fix millisecond timestamps (#6001)


4.3.27 (2017-09-18)
===================

Bug fixes
^^^^^^^^^

* Fix #5980 always delete_prefix_from_linked_data in rm_rf (#5982)


4.3.26 (2017-09-15)
===================

Deprecations/Breaking changes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Resolve #5922 prioritize channels within multi-channels (#5923)
* Add https://repo.continuum.io/pkgs/main to defaults multi-channel (#5931)

Improvements
^^^^^^^^^^^^

* Add a channel priority minimization pass to solver logic (#5859)
* Invoke cmd.exe with /D for pre/post link/unlink scripts (#5926)
* Add boto3 use to s3 adapter (#5949)

Bug fixes
^^^^^^^^^

* Always remove linked prefix entry with rm_rf (#5846)
* Resolve #5920 bump repodata pickle version (#5921)
* Fix msys2 activate and deactivate (#5950)


4.3.25 (2017-08-16)
===================

Deprecations/Breaking changes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Resolve #5834 change default value of 'allow_softlinks' from True to False (#5839)

Improvements
^^^^^^^^^^^^

* Add non-admin check to optionally disable non-privileged operation (#5724)
* Add extra warning message to always_softlink configuration option (#5826)

Bug fixes
^^^^^^^^^

* Fix #5763 channel url string splitting error (#5764)
* Fix regex for repodata _mod and _etag (#5795)
* Fix uncaught OSError for missing device (#5830)


4.3.24 (2017-07-31)
===================

Bug fixes
^^^^^^^^^

* Fix #5708 package priority sort order (#5733)


4.3.23 (2017-07-21)
===================

Improvements
^^^^^^^^^^^^

* Resolve #5391 PackageNotFound and NoPackagesFoundError clean up (#5506)

Bug fixes
^^^^^^^^^

* Fix #5525 too many Nones in CondaHttpError (#5526)
* Fix #5508 assertion failure after test file not cleaned up (#5533)
* Fix #5523 catch OSError when home directory doesn't exist (#5549)
* Fix #5574 traceback formatting (#5580)
* Fix #5554 logger configuration levels (#5555)
* Fix #5649 create_default_packages configuration (#5703)


4.3.22 (2017-06-12) 
===================

Improvements
^^^^^^^^^^^^

* Resolve #5428 clean up cli import in conda 4.3.x (#5429)
* Resolve #5302 add warning when creating environment with space in path (#5477)
* For ftp connections, ignore host IP from PASV as it is often wrong (#5489)
* Expose common race condition exceptions in exports for conda-build (#5498)

Bug fixes
^^^^^^^^^

* Fix #5451 conda clean --json bug (#5452)
* Fix #5400 confusing deactivate message (#5473)
* Fix #5459 custom subdir channel parsing (#5478)
* Fix #5483 problem with setuptools / pkg_resources import (#5496)


4.3.21 (2017-05-25)
===================

Bug fixes
^^^^^^^^^

* Fix #5420 conda-env update error (#5421)
* Fix #5425 is admin on win int not callable (#5426)


4.3.20 (2017-05-23)
===================

Improvements
^^^^^^^^^^^^

* Resolve #5217 skip user confirm in python_api, force always_yes (#5404)

Bug fixes
^^^^^^^^^

* Fix #5367 conda info always shows 'unknown' for admin indicator on Windows (#5368)
* Fix #5248 drop plan description information that might not alwasy be accurate (#5373)
* Fix #5378 duplicate log messages (#5379)
* Fix #5298 record has 'build', not 'build_string' (#5382)
* Fix #5384 silence logging info to avoid interfering with JSON output (#5393)
* Fix #5356 skip root/conda logger init for cli.python_api (#5405)

Non-user-facing changes
^^^^^^^^^^^^^^^^^^^^^^^

* Avoid persistent state after channel priority test (#5392)
* Resolve #5402 add regression test for #5384 (#5403)
* Clean up inner function definition inside for loop (#5406)


4.3.19 (2017-05-18)
===================

Improvements
^^^^^^^^^^^^

* Resolve #3689 better error messaging for missing anaconda-client (#5276)
* Resolve #4795 conda env export lacks -p flag (#5275)
* Resolve #5315 add alias verify_ssl for ssl_verify (#5316)
* Resolve #3399 add netrc existence/location to 'conda info' (#5333)
* Resolve #3810 add --prefix to conda env update (#5335)

Bug fixes
^^^^^^^^^

* Fix #5272 conda env export ugliness under python2 (#5273)
* Fix #4596 warning message from pip on conda env export (#5274)
* Fix #4986 --yes not functioning for conda clean (#5311)
* Fix #5329 unicode errors on Windows (#5328, #5357)
* Fix sys_prefix_unfollowed for Python 3 (#5334)
* Fix #5341 --json flag with conda-env (#5342)
* Fix 5321 ensure variable PROMPT is set in activate.bat (#5351)

Non-user-facing changes
^^^^^^^^^^^^^^^^^^^^^^^

* Test conda 4.3 with requests 2.14.2 (#5281)
* Remove pycrypto as requirement on Windows (#5325)
* Fix typo avaialble -> available (#5345)
* Fix test failures related to menuinst update (#5344, #5362)


4.3.18 (2017-05-09)
===================

Improvements
^^^^^^^^^^^^

* Resolve #4224 warn when pysocks isn't installed (#5226)
* Resolve #5229 add --insecure flag to skip ssl verification (#5230)
* Resolve #4151 add admin indicator to conda info on windows (#5241)

Bug fixes
^^^^^^^^^

* Fix #5152 conda info spacing (#5166)
* Fix --use-index-cache actually hitting the index cache (#5134)
* Backport LinkPathAction verify from 4.4 (#5171)
* Fix #5184 stack trace on invalid map configuration parameter (#5186)
* Fix #5189 stack trace on invalid sequence config param (#5192)
* Add support for the linux-aarch64 platform (#5190)
* Fix repodata fetch with the `--offline` flag (#5146)
* Fix #1773 conda remove spell checking (#5176)
* Fix #3470 reduce excessive error messages (#5195)
* Fix #1597 make extra sure --dry-run doesn't take any actions (#5201)
* Fix #3470 extra newlines around exceptions (#5200)
* Fix #5214 install messages for 'nothing_to_do' case (#5216)
* Fix #598 stack trace for condarc write permission denied (#5232)
* Fix #4960 extra information when exception can't be displayed (#5236)
* Fix #4974 no matching dist in linked data for prefix (#5239)
* Fix #5258 give correct element types for conda config --describe (#5259)
* Fix #4911 separate shutil.copy2 into copy and copystat (#5261)

Non-user-facing changes
^^^^^^^^^^^^^^^^^^^^^^^

* Resolve #5138 add test of rm_rf of symlinked files (#4373)
* Resolve #4516 add extra trace-level logging (#5249, #5250)
* Add tests for --update-deps flag (#5264)


4.3.17 (2017-04-24)
===================

Improvements
^^^^^^^^^^^^

* Fall back to copy if hardlink fails (#5002)
* Add timestamp metadata for tiebreaking conda-build 3 hashed packages (#5018)
* Resolve #5034 add subdirs configuration parameter (#5030)
* Resolve #5081 make pinned packages optional/constrained dependencies (#5088)
* Resolve #5108 improve behavior and add tests for spaces in paths (#4786)

Bug fixes
^^^^^^^^^

* Quote prefix paths for locations with spaces (#5009)
* Remove binstar logger configuration overrides (#4989)
* Fix #4969 error in DirectoryNotFoundError (#4990)
* Fix #4998 pinned string format (#5011)
* Fix #5039 collecting main_info shouldn't fail on requests import (#5090)
* Fix #5055 improve bad token message for anaconda.org (#5091)
* Fix #5033 only re-register valid signal handlers (#5092)
* Fix #5028 imports in main_list (#5093)
* Fix #5073 allow client_ssl_cert{_key} to be of type None (#5096)
* Fix #4671 backoff for package validate race condition (#5098)
* Fix #5022 gnu_get_libc_version => linux_get_libc_version (#5099)
* Fix #4849 package name match bug (#5103)
* Fixes #5102 allow proxy_servers to be of type None (#5107)
* Fix #5111 incorrect typify for str + NoneType (#5112)

Non-user-facing changes
^^^^^^^^^^^^^^^^^^^^^^^

* Resolve #5012 remove CondaRuntimeError and RuntimeError (#4818)
* Full audit ensuring relative import paths within project (#5090)
* Resolve #5116 refactor conda/cli/activate.py to help menuinst (#4406)


4.3.16 (2017-03-30)
===================

Improvements
^^^^^^^^^^^^

* Additions to configuration SEARCH_PATH to improve consistency (#4966)
* Add 'conda config --describe' and extra config documentation (#4913)
* Enable packaging pinning in condarc using pinned_packages config parameter
  as beta feature (#4921, #4964)

Bug fixes
^^^^^^^^^

* Fix #4914 handle directory creation on top of file paths (#4922)
* Fix #3982 issue with CONDA_ENV and using powerline (#4925)
* Fix #2611 update instructions on how to source conda.fish (#4924)
* Fix #4860 missing information on package not found error (#4935)
* Fix #4944 command not found error error (#4963)


4.3.15 (2017-03-20)
===================

Improvements
^^^^^^^^^^^^

* Allow pkgs_dirs to be configured using `conda config` (#4895)

Bug fixes
^^^^^^^^^

* Remove incorrect elision of delete_prefix_from_linked_data() (#4814)
* Fix envs_dirs order for read-only root prefix (#4821)
* Fix break-point in conda clean (#4801)
* Fix long shebangs when creating entry points (#4828)
* Fix spelling and typos (#4868, #4869)
* Fix #4840 TypeError reduce() of empty sequence with no initial value (#4843)
* Fix zos subdir (#4875)
* Fix exceptions triggered during activate (#4873)


4.3.14 (2017-03-03)
===================

Improvements
^^^^^^^^^^^^

* Use cPickle in place of pickle for repodata (#4717)
* Ignore pyc compile failure (#4719)
* Use conda.exe for windows entry point executable (#4716, #4720)
* Localize use of conda_signal_handler (#4730)
* Add skip_safety_checks configuration parameter (#4767)
* Never symlink executables using ORIGIN (#4625)
* Set activate.bat codepage to CP_ACP (#4558)

Bug fixes
^^^^^^^^^

* Fix #4777 package cache initialization speed (#4778)
* Fix #4703 menuinst PathNotFoundException (#4709)
* Ignore permissions error if user_site can't be read (#4710)
* Fix #4694 don't import requests directly in models (#4711)
* Fix #4715 include resources directory in recipe (#4716)
* Fix CondaHttpError for URLs that contain '%' (#4769)
* Bug fixes for preferred envs (#4678)
* Fix #4745 check for info/index.json with package is_extracted (#4776)
* Make sure url gets included in CondaHTTPError (#4779)
* Fix #4757 map-type configs set to None (#4774)
* Fix #4788 partial package extraction (#4789)

Non-user-facing changes
^^^^^^^^^^^^^^^^^^^^^^^

* Test coverage improvement (#4607)
* CI configuration improvements (#4713, #4773, #4775)
* Allow sha256 to be None (#4759)
* Add cache_fn_url to exports (#4729)
* Add unicode paths for PY3 integration tests (#4760)
* Additional unit tests (#4728, #4783)
* Fix conda-build compatibility and tests (#4785)


4.3.13 (2017-02-17)
===================

Improvements
^^^^^^^^^^^^

* Resolve #4636 environment variable expansion for pkgs_dirs (#4637)
* Link, symlink, islink, and readlink for Windows (#4652, #4661)
* Add extra information to CondaHTTPError (#4638, #4672)

Bug fixes
^^^^^^^^^

* Maximize requested builds after feature determination (#4647)
* Fix #4649 incorrect assert statement concerning package cache directory (#4651)
* Multi-user mode bug fixes (#4663)

Non-user-facing changes
^^^^^^^^^^^^^^^^^^^^^^^

* Path_actions unit tests (#4654)
* Remove dead code (#4369, #4655, #4660)
* Separate repodata logic from index into a new core/repodata.py module (#4669)


4.3.12 (2017-02-14)
===================

Improvements
^^^^^^^^^^^^

* Prepare conda for uploading to PyPI (#4619)
* Better general http error message (#4627)
* Disable old Python noarch warning (#4576)

Bug fixes
^^^^^^^^^

* Fix UnicodeDecodeError for ensure_text_type (#4585)
* Fix determination of if file path is writable (#4604)
* Fix #4592 BufferError cannot close exported pointers exist (#4628)
* Fix run_script current working directory (#4629)
* Fix pkgs_dirs permissions regression (#4626)

Non-user-facing changes
^^^^^^^^^^^^^^^^^^^^^^^

* Fixes for tests when conda-bld directory doesn't exist (#4606)
* Use requirements.txt and Makefile for travis-ci setup (#4600, #4633)
* Remove hasattr use from compat functions (#4634)


4.3.11 (2017-02-09)
===================

Bug fixes
^^^^^^^^^

* Fix attribute error in add_defaults_to_specs (#4577)


4.3.10 (2017-02-07)
===================

Improvements
^^^^^^^^^^^^

* Remove .json from pickle path (#4498)
* Improve empty repodata noarch warning and error messages (#4499)
* Don't add Python and lua as default specs for private envs (#4529, #4533)
* Let default_python be None (#4547, #4550)

Bug fixes
^^^^^^^^^

* Fix #4513 null pointer exception for channel without noarch (#4518)
* Fix ssl_verify set type (#4517)
* Fix bug for Windows multiuser (#4524)
* Fix clone with noarch Python packages (#4535)
* Fix ipv6 for Python 2.7 on Windows (#4554)

Non-user-facing changes
^^^^^^^^^^^^^^^^^^^^^^^

* Separate integration tests with a marker (#4532)


4.3.9 (2017-01-31)
==================

Improvements
^^^^^^^^^^^^

* Improve repodata caching for performance (#4478, #4488)
* Expand scope of packages included by bad_installed (#4402)
* Silence pre-link warning for old noarch (#4451)
* Add configuration to optionally require noarch repodata (#4450)
* Improve conda subprocessing (#4447)
* Respect info/link.json (#4482)

Bug fixes
^^^^^^^^^

* Fix #4398 'hard' was used for link type at one point (#4409)
* Fixed "No matches for wildcard '$activate_d/\*.fish'" warning (#4415)
* Print correct activate/deactivate message for fish shell (#4423)
* Fix 'Dist' object has no attribute 'fn' (#4424)
* Fix noarch generic and add additional integration test (#4431)
* Fix #4425 unknown encoding (#4433)

Non-user-facing changes
^^^^^^^^^^^^^^^^^^^^^^^

* Fail CI on conda-build fail (#4405)
* Run doctests (#4414)
* Make index record mutable again (#4461)
* Additional test for conda list --json (#4480)


4.3.8 (2017-01-23)
==================

Bug fixes
^^^^^^^^^

* Fix #4309 ignore EXDEV error for directory renames (#4392)
* Fix #4393 by force-renaming certain backup files if the path already exists (#4397)


4.3.7 (2017-01-20)
==================

Bug fixes
^^^^^^^^^

* Actually revert JSON output for leaky plan (#4383)
* Fix not raising on pre/post-link error (#4382)
* Fix find_commands and find_executable for symlinks (#4387)


4.3.6 (2017-01-18)
==================

Bug fixes
^^^^^^^^^

* Fix 'Uncaught backoff with errno 41' warning on windows (#4366)
* Revert json output for leaky plan (#4349)
* Audit os.environ setting (#4360)
* Fix #4324 using old dist string instead of dist object (#4361)
* Fix #4351 infinite recursion via code in #4120 (#4370)
* Fix #4368 conda -h (#4367)
* Workaround for symlink race conditions on activate (#4346)


4.3.5 (2017-01-17)
==================

Improvements
^^^^^^^^^^^^

* Add exception message for corrupt repodata (#4315)

Bug fixes
^^^^^^^^^

* Fix package not being found in cache after download (#4297)
* Fix logic for Content-Length mismatch (#4311, #4326)
* Use unicode_escape after etag regex instead of utf-8 (#4325)
* Fix #4323 central condarc file being ignored (#4327)
* Fix #4316 a bug in deactivate (#4316)
* Pass target_prefix as env_prefix regardless of is_unlink (#4332)
* Pass positional argument 'context' to BasicClobberError (#4335)

Non-user-facing changes
^^^^^^^^^^^^^^^^^^^^^^^

* Additional package pinning tests (#4317)

4.3.4 (2017-01-13)
==================

Improvements
^^^^^^^^^^^^

* Vendor url parsing from urllib3 (#4289)

Bug fixes
^^^^^^^^^

* Fix some bugs in windows multi-user support (#4277)
* Fix problems with channels of type <unknown> (#4290)
* Include aliases for first command-line argument (#4279)
* Fix for multi-line FTP status codes (#4276)

Non-user-facing changes
^^^^^^^^^^^^^^^^^^^^^^^

* Make arch in IndexRecord a StringField instead of EnumField
* Improve conda-build compatibility (#4266)


4.3.3 (2017-01-10)
==================

Improvements
^^^^^^^^^^^^

* Respect Cache-Control max-age header for repodata (#4220)
* Add 'local_repodata_ttl' configurability (#4240)
* Remove questionable "nothing to install" logic (#4237)
* Relax channel noarch requirement for 4.3; warn now, raise in future feature release (#4238)
* Add additional info to setup.py warning message (#4258)

Bug fixes
^^^^^^^^^

* Remove features properly (#4236)
* Do not use `IFS` to find activate/deactivate scripts to source (#4239)
* Fix #4235 print message to stderr (#4241)
* Fix relative path to Python in activate.bat (#4242)
* Fix args.channel references (#4245, #4246)
* Ensure cache_fn_url right pad (#4255)
* Fix #4256 subprocess calls must have env wrapped in str (#4259)


4.3.2 (2017-01-06)
==================

Deprecations/Breaking changes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Further refine conda channels specification. To verify if the url of a channel
  represents a valid conda channel, we check that `noarch/repodata.json` and/or
  `noarch/repodata.json.bz2` exist, even if empty. (#3739)

Improvements
^^^^^^^^^^^^

* Add new 'path_conflict' and 'clobber' configuration options (#4119)
* Separate fetch/extract pass for explicit URLs (#4125)
* Update conda homepage to conda.io (#4180)

Bug fixes
^^^^^^^^^

* Fix pre/post unlink/link scripts (#4113)
* Fix package version regex and bug in create_link (#4132)
* Fix history tracking (#4143)
* Fix index creation order (#4131)
* Fix #4152 conda env export failure (#4175)
* Fix #3779 channel UNC path encoding errors on windows (#4190)
* Fix progress bar (#4191)
* Use context.channels instead of args.channel (#4199)
* Don't use local cached repodata for file:// urls (#4209)

Non-user-facing changes
^^^^^^^^^^^^^^^^^^^^^^^

* Xfail anaconda token test if local token is found (#4124)
* Fix open-ended test failures relating to Python 3.6 release (#4145)
* Extend timebomb for test_multi_channel_export (#4169)
* Don't unlink dists that aren't in the index (#4130)
* Add Python 3.6 and new conda-build test targets (#4194)


4.3.1 (2016-12-19)
==================

Improvements
^^^^^^^^^^^^

* Additional pre-transaction validation (#4090)
* Export FileMode enum for conda-build (#4080)
* Memoize disk permissions tests (#4091)
* Local caching of repodata without remote server calls; new 'repodata_timeout_secs'
  configuration parameter (#4094)
* Performance tuning (#4104)
* Add additional fields to dist object serialization (#4102)

Bug fixes
^^^^^^^^^

* Fix a noarch install bug on windows (#4071)
* Fix a spec mismatch that resulted in Python versions getting mixed during packaging (#4079)
* Fix rollback linked record (#4092)
* Fix #4097 keep split in PREFIX_PLACEHOLDER (#4100)


4.3.0 (2016-12-14) Safety
=========================

New features
^^^^^^^^^^^^

* **Unlink and Link Packages in a Single Transaction**: In the past, conda hasn't always been safe
  and defensive with its disk-mutating actions. It has gleefully clobbered existing files, and
  mid-operation failures leave environments completely broken. In some of the most severe examples,
  conda can appear to "uninstall itself." With this release, the unlinking and linking of packages
  for an executed command is done in a single transaction. If a failure occurs for any reason
  while conda is mutating files on disk, the environment will be returned its previous state.
  While we've implemented some pre-transaction checks (verifying package integrity for example),
  it's impossible to anticipate every failure mechanism. In some circumstances, OS file
  permissions cannot be fully known until an operation is attempted and fails. And conda itself
  is not without bugs. Moving forward, unforeseeable failures won't be catastrophic. (#3833, #4030)

* **Progressive Fetch and Extract Transactions**: Like package unlinking and linking, the
  download and extract phases of package handling have also been given transaction-like behavior.
  The distinction is the rollback on error is limited to a single package. Rather than rolling back
  the download and extract operation for all packages, the single-package rollback prevents the
  need for having to re-download every package if an error is encountered. (#4021, #4030)

* **Generic- and Python-Type Noarch/Universal Packages**: Along with conda-build 2.1.0, a
  noarch/universal type for Python packages is officially supported. These are much like universal
  Python wheels. Files in a Python noarch package are linked into a prefix just like any other
  conda package, with the following additional features:

  1. conda maps the `site-packages` directory to the correct location for the Python version
     in the environment,
  2. conda maps the Python-scripts directory to either $PREFIX/bin or $PREFIX/Scripts depending
     on platform,
  3. conda creates the Python entry points specified in the conda-build recipe, and
  4. conda compiles pyc files at install time when prefix write permissions are guaranteed.

  Python noarch packages must be "fully universal."  They cannot have OS- or
  Python version-specific dependencies.  They cannot have OS- or Python version-specific "scripts"
  files. If these features are needed, traditional conda packages must be used. (#3712)

* **Multi-User Package Caches**: While the on-disk package cache structure has been preserved,
  the core logic implementing package cache handling has had a complete overhaul.  Writable and
  read-only package caches are fully supported. (#4021)

* **Python API Module**: An oft requested feature is the ability to use conda as a Python library,
  obviating the need to "shell out" to another Python process. Conda 4.3 includes a
  `conda.cli.python_api` module that facilitates this use case. While we maintain the user-facing
  command-line interface, conda commands can be executed in-process. There is also a
  `conda.exports` module to facilitate longer-term usage of conda as a library across conda
  conda releases.  However, conda's Python code *is* considered internal and private, subject
  to change at any time across releases. At the moment, conda will not install itself into
  environments other than its original install environment. (#4028)

* **Remove All Locks**:  Locking has never been fully effective in conda, and it often created a
  false sense of security. In this release, multi-user package cache support has been
  implemented for improved safety by hard-linking packages in read-only caches to the user's
  primary user package cache. Still, users are cautioned that undefined behavior can result when
  conda is running in multiple process and operating on the same package caches and/or
  environments. (#3862)

Deprecations/Breaking changes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Conda now has the ability to refuse to clobber existing files that are not within the unlink
  instructions of the transaction.  This behavior is configurable via the `path_conflict`
  configuration option, which has three possible values: `clobber`, `warn`, and `prevent`. In 4.3,
  the default value will be `clobber`.  That will give package maintainers time to correct current
  incompatibilities within their package ecosystem. In 4.4, the default will switch to `warn`,
  which means these operations continue to clobber, but the warning messages are displayed.  In
  `4.5`, the default value will switch to `prevent`.  As we tighten up the `path_conflict`
  constraint, a new command line flag `--clobber` will loosen it back up on an *ad hoc* basis.
  Using `--clobber` overrides the setting for `path_conflict` to effectively be `clobber` for
  that operation.
* Conda signed packages have been removed in 4.3. Vulnerabilities existed. An illusion of security
  is worse than not having the feature at all.  We will be incorporating The Update Framework
  into conda in a future feature release. (#4064)
* Conda 4.4 will drop support for older versions of conda-build.

Improvements
^^^^^^^^^^^^

* Create a new "trace" log level enabled by `-v -v -v` or `-vvv` (#3833)
* Allow conda to be installed with pip, but only when used as a library/dependency (#4028)
* The 'r' channel is now part of defaults (#3677)
* Private environment support for conda (#3988)
* Support v1 info/paths.json file (#3927, #3943)
* Support v1 info/package_metadata.json (#4030)
* Improved solver hint detection, simplified filtering (#3597)
* Cache VersionOrder objects to improve performance (#3596)
* Fix documentation and typos (#3526, #3572, #3627)
* Add multikey configuration validation (#3432)
* Some Fish autocompletions (#2519)
* Reduce priority for packages removed from the index (#3703)
* Add user-agent, uid, gid to conda info (#3671)
* Add conda.exports module (#3429)
* Make http timeouts configurable (#3832)
* Add a pkgs_dirs config parameter (#3691)
* Add an 'always_softlink' option (#3870, #3876)
* Pre-checks for diskspace, etc for fetch and extract #(4007)
* Address #3879 don't print activate message when quiet config is enabled (#3886)
* Add zos-z subdir (#4060)
* Add elapsed time to HTTP errors (#3942)

Bug fixes
^^^^^^^^^

* Account for the Windows Python 2.7 os.environ unicode aversion (#3363)
* Fix link field in record object (#3424)
* Anaconda api token bug fix; additional tests (#3673)
* Fix #3667 unicode literals and unicode decode (#3682)
* Add conda-env entrypoint (#3743)
* Fix #3807 json dump on ``conda config --show --json`` (#3811)
* Fix #3801 location of temporary hard links of index.json (#3813)
* Fix invalid yml example (#3849)
* Add arm platforms back to subdirs (#3852)
* Fix #3771 better error message for assertion errors (#3802)
* Fix #3999 spaces in shebang replacement (#4008)
* Config --show-sources shouldn't show force by default (#3891)
* Fix #3881 don't install conda-env in clones of root (#3899)
* Conda-build dist compatibility (#3909)

Non-user-facing changes
^^^^^^^^^^^^^^^^^^^^^^^

* Remove unnecessary eval (#3428)
* Remove dead install_tar function (#3641)
* Apply PEP-8 to conda-env (#3653)
* Refactor dist into an object (#3616)
* Vendor appdirs; remove conda's dependency on anaconda-client import (#3675)
* Revert boto patch from #2380 (#3676)
* Move and update ROOT_NO_RM (#3697)
* Integration tests for conda clean (#3695, #3699)
* Disable coverage on s3 and ftp requests adapters (#3696, #3701)
* Github repo hygiene (#3705, #3706)
* Major install refactor (#3712)
* Remove test timebombs (#4012)
* LinkType refactor (#3882)
* Move CrossPlatformStLink and make available as export (#3887)
* Make Record immutable (#3965)
* Project housekeeping (#3994, #4065)
* Context-dependent setup.py files (#4057)


4.2.15 (2017-01-10)
===================

Improvements
^^^^^^^^^^^^

* Use 'post' instead of 'dev' for commits according to PEP-440 (#4234)
* Do not use IFS to find activate/deactivate scripts to source (#4243)
* Fix relative path to Python in activate.bat (#4244)

Bug fixes
^^^^^^^^^

* Replace sed with Python for activate and deactivate #4257


4.2.14 (2017-01-07)
===================

Improvements
^^^^^^^^^^^^

* Use install.rm_rf for TemporaryDirectory cleanup (#3425)
* Improve handling of local dependency information (#2107)
* Add default channels to exports for Windows Linux and macOS (#4103)
* Make subdir configurable (#4178)

Bug fixes
^^^^^^^^^

* Fix conda/install.py single-file behavior (#3854)
* Fix the api->conda substitution (#3456)
* Fix silent directory removal (#3730)
* Fix location of temporary hard links of index.json (#3975)
* Fix potential errors in multi-channel export and offline clone (#3995)
* Fix auxlib/packaging, git hashes are not limited to 7 characters (#4189)
* Fix compatibility with requests >=2.12, add pyopenssl as dependency (#4059)
* Fix #3287 activate in 4.1-4.2.3 clobbers non-conda PATH changes (#4211)

Non-user-facing changes
^^^^^^^^^^^^^^^^^^^^^^^

* Fix open-ended test failures relating to Python 3.6 release (#4166)
* Allow args passed to cli.main() (#4193, #4200, #4201)
* Test against Python 3.6 (#4197)


4.2.13 (2016-11-22)
===================

Deprecations/Breaking changes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Show warning message for pre-link scripts (#3727)
* Error and exit for install of packages that require conda minimum version 4.3 (#3726)

Improvements
^^^^^^^^^^^^

* Double/extend http timeouts (#3831)
* Let descriptive http errors cover more http exceptions (#3834)
* Backport some conda-build configuration (#3875)

Bug fixes
^^^^^^^^^

* Fix conda/install.py single-file behavior (#3854)
* Fix the api->conda substitution (#3456)
* Fix silent directory removal (#3730)
* Fix #3910 null check for is_url (#3931)

Non-user-facing changes
^^^^^^^^^^^^^^^^^^^^^^^

* Flake8 E116, E121, & E123 enabled (#3883)


4.2.12 (2016-11-02)
===================

Bug fixes
^^^^^^^^^

* Fix #3732, #3471, #3744 CONDA_BLD_PATH (#3747)
* Fix #3717 allow no-name channels (#3748)
* Fix #3738 move conda-env to ruamel_yaml (#3740)
* Fix conda-env entry point (#3745 via #3743)
* Fix again #3664 trash emptying (#3746)


4.2.11 (2016-10-23)
===================

Improvements
^^^^^^^^^^^^

* Only try once for Windows trash removal (#3698)

Bug fixes
^^^^^^^^^

* Fix Anaconda api token bug (#3674)
* Fix #3646 FileMode enum comparison (#3683)
* Fix #3517 ``conda install --mkdir`` (#3684)
* Fix #3560 hack Anaconda token coverup on conda info (#3686)
* Fix #3469 alias envs_path to envs_dirs (#3685)


4.2.10 (2016-10-18)
===================

Improvements
^^^^^^^^^^^^

* Add JSON output for ``conda info -s`` (#3588)
* Ignore certain binary prefixes on Windows (#3539)
* Allow conda config files to have .yaml extensions or 'condarc' anywhere in filename (#3633)

Bug fixes
^^^^^^^^^

* Fix conda-build's handle_proxy_407 import (#3666)
* Fix #3442, #3459, #3481, #3531, #3548 multiple networking and auth issues (#3550)
* Add back linux-ppc64le subdir support (#3584)
* Fix #3600 ensure links are removed when unlinking (#3625)
* Fix #3602 search channels by platform (#3629)
* Fix duplicated packages when updating environment (#3563)
* Fix #3590 exception when parsing invalid yaml (#3593 via #3634)
* Fix #3655 a string decoding error (#3656)

Non-user-facing changes
^^^^^^^^^^^^^^^^^^^^^^^

* Backport conda.exports module to 4.2.x (#3654)
* Travis-ci OSX fix (#3615 via #3657)


4.2.9 (2016-09-27)
==================

Bug fixes
^^^^^^^^^

* Fix #3536 conda-env messaging to stdout with ``--json`` flag (#3537)
* Fix #3525 writing to sys.stdout with ``--json`` flag for post-link scripts (#3538)
* Fix #3492 make NULL falsey with Python 3 (#3524)


4.2.8 (2016-09-26)
==================

Improvements
^^^^^^^^^^^^

* Add "error" key back to json error output (#3523)

Bug fixes
^^^^^^^^^

* Fix #3453 conda fails with create_default_packages (#3454)
* Fix #3455 ``--dry-run`` fails (#3457)
* Dial down error messages for rm_rf (#3522)
* Fix #3467 AttributeError encountered for map config parameter validation (#3521)


4.2.7 (2016-09-16)
==================

Deprecations/Breaking changes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Revert to 4.1.x behavior of ``conda list --export`` (#3450, #3451)

Bug fixes
^^^^^^^^^

* Don't add binstar token if it's given in the channel spec (#3427, #3440, #3444)
* Fix #3433 failure to remove broken symlinks (#3436)

Non-user-facing changes
^^^^^^^^^^^^^^^^^^^^^^^

* Use install.rm_rf for TemporaryDirectory cleanup (#3425)


4.2.6 (2016-09-14)
==================

Improvements
^^^^^^^^^^^^

* Add support for client TLS certificates (#3419)
* Address #3267 allow migration of channel_alias (#3410)
* conda-env version matches conda version (#3422)

Bug fixes
^^^^^^^^^

* Fix #3409 unsatisfiable dependency error message (#3412)
* Fix #3408 quiet rm_rf (#3413)
* Fix #3407 padding error messaging (#3416)
* Account for the Windows Python 2.7 os.environ unicode aversion (#3363 via #3420)


4.2.5 (2016-09-08)
==================

Deprecations/Breaking changes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Partially revert #3041 giving conda config --add previous --prepend behavior (#3364 via #3370)
* Partially revert #2760 adding back conda package command (#3398)

Improvements
^^^^^^^^^^^^

* Order output of ``conda config --show``; make ``--json`` friendly (#3384 via #3386)
* Clean the pid based lock on exception (#3325)
* Improve file removal on all platforms (#3280 via #3396)

Bug fixes
^^^^^^^^^

* Fix #3332 allow download urls with ``::`` in them (#3335)
* Fix always_yes and not-set argparse args overriding other sources (#3374)
* Fix ftp fetch timeout (#3392)
* Fix #3307 add try/except block for touch lock (#3326)
* Fix CONDA_CHANNELS environment variable splitting (#3390)
* Fix #3378 CONDA_FORCE_32BIT environment variable (#3391)
* Make conda info channel urls actually give urls (#3397)
* Fix cio_test compatibility (#3395 via #3400)


4.2.4 (2016-08-18)
==================

Bug fixes
^^^^^^^^^

* Fix #3277 conda list package order (#3278)
* Fix channel priority issue with duplicated channels (#3283)
* Fix local channel channels; add full conda-build unit tests (#3281)
* Fix conda install with no package specified (#3284)
* Fix #3253 exporting and importing conda environments (#3286)
* Fix priority messaging on ``conda config --get`` (#3304)
* Fix ``conda list --export``; additional integration tests (#3291)
* Fix ``conda update --all`` idempotence; add integration tests for channel priority (#3306)

Non-user-facing changes
^^^^^^^^^^^^^^^^^^^^^^^

* Additional conda-env integration tests (#3288)


4.2.3 (2016-08-11)
==================

Improvements
^^^^^^^^^^^^

* Added zsh and zsh.exe to Windows shells (#3257)

Bug fixes
^^^^^^^^^

* Allow conda to downgrade itself (#3273)
* Fix breaking changes to conda-build from 4.2.2 (#3265)
* Fix empty environment issues with conda and conda-env (#3269)

Non-user-facing changes
^^^^^^^^^^^^^^^^^^^^^^^

* Add integration tests for conda-env (#3270)
* Add more conda-build smoke tests (#3274)


4.2.2 (2016-08-09)
==================

Improvements
^^^^^^^^^^^^

* Enable binary prefix replacement on windows (#3262)
* Add ``--verbose`` command line flag (#3237)
* Improve logging and exception detail (#3237, #3252)
* Do not remove empty environment without asking; raise an error when a named environment can't be found (#3222)

Bug fixes
^^^^^^^^^

* Fix #3226 user condarc not available on Windows (#3228)
* Fix some bugs in conda config --show* (#3212)
* Fix conda-build local channel bug (#3202)
* remove subprocess exiting message (#3245)
* Fix comment parsing and channels in conda-env environment.yml (#3258, #3259)
* Fix context error with conda-env (#3232)
* Fix #3182 conda install silently skipping failed linking (#3184)


4.2.1 (2016-08-01)
==================

Improvements
^^^^^^^^^^^^

* Improve an error message that can happen during conda install --revision (#3181)
* Use clean sys.exit with user choice 'No' (#3196)

Bug fixes
^^^^^^^^^

* Critical fix for 4.2.0 error when no git is on PATH (#3193)
* Revert #3171 lock cleaning on exit pending further refinement
* Patches for conda-build compatibility with 4.2 (#3187)
* Fix a bug in --show-sources output that ignored aliased parameter names (#3189)

Non-user-facing changes
^^^^^^^^^^^^^^^^^^^^^^^

* Move scripts in bin to shell directory (#3186)


4.2.0 (2016-07-28)
==================

New features
^^^^^^^^^^^^

* **New Configuration Engine**: Configuration and "operating context" are the foundation of conda's functionality. Conda now has the ability to pull configuration information from a multitude of on-disk locations, including ``.d`` directories and a ``.condarc`` file *within* a conda environment), along with full ``CONDA_`` environment variable support. Helpful validation errors are given for improperly-specified configuration. Full documentation updates pending. (#2537, #3160, #3178)
* **New Exception Handling Engine**: Previous releases followed a pattern of premature exiting (with hard calls to ``sys.exit()``) when exceptional circumstances were encountered. This release replaces over 100 ``sys.exit`` calls with Python exceptions.  For conda developers, this will result in tests that are easier to write.  For developers using conda, this is a first step on a long path toward conda being directly importable.  For conda users, this will eventually result in more helpful and descriptive errors messages.  (#2899, #2993, #3016, #3152, #3045)
* **Empty Environments**: Conda can now create "empty" environments when no initial packages are specified, alleviating a common source of confusion. (#3072, #3174)
* **Conda in Private Env**: Conda can now be configured to live within its own private environment.  While it's not yet default behavior, this represents a first step toward separating the ``root`` environment into a "conda private" environment and a "user default" environment. (#3068)
* **Regex Version Specification**: Regular expressions are now valid version specifiers.  For example, ``^1\.[5-8]\.1$|2.2``. (#2933)

Deprecations/Breaking changes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Remove conda init (#2759)
* Remove conda package and conda bundle (#2760)
* Deprecate conda-env repo; pull into conda proper (#2950, #2952, #2954, #3157, #3163, #3170)
* Force use of ruamel_yaml (#2762)
* Implement conda config --prepend; change behavior of --add to --append (#3041)
* Exit on link error instead of logging it (#2639)

Improvements
^^^^^^^^^^^^

* Improve locking (#2962, #2989, #3048, #3075)
* Clean up requests usage for fetching packages (#2755)
* Remove excess output from conda --help (#2872)
* Remove os.remove in update_prefix (#3006)
* Better error behavior if conda is spec'd for a non-root environment (#2956)
* Scale back try_write function on Linux and macOS (#3076)

Bug fixes
^^^^^^^^^

* Remove psutil requirement, fixes annoying error message (#3135, #3183)
* Fix #3124 add threading lock to memoize (#3134)
* Fix a failure with multi-threaded repodata downloads (#3078)
* Fix windows file url (#3139)
* Address #2800, error with environment.yml and non-default channels (#3164)

Non-user-facing changes
^^^^^^^^^^^^^^^^^^^^^^^

* Project structure enhancement (#2929, #3132, #3133, #3136)
* Clean up channel handling with new channel model (#3130, #3151)
* Add Anaconda Cloud / Binstar auth handler (#3142)
* Remove dead code (#2761, #2969)
* Code refactoring and additional tests (#3052, #3020)
* Remove auxlib from project root (#2931)
* Vendor auxlib 0.0.40 (#2932, #2943, #3131)
* Vendor toolz 0.8.0 (#2994)
* Move progressbar to vendor directory (#2951)
* Fix conda.recipe for new quirks with conda-build (#2959)
* Move captured function to common module (#3083)
* Rename CHANGELOG to md (#3087)


4.1.12 (2016-09-08)
===================

* Fix #2837 "File exists" in symlinked path with parallel activations, #3210
* Fix prune option when installing packages, #3354
* Change check for placeholder to be more friendly to long PATH, #3349


4.1.11 (2016-07-26)
===================

* Fix PS1 backup in activate script, #3135 via #3155
* Correct resolution for 'handle failures in binstar_client more generally', #3156


4.1.10 (2016-07-25)
===================

* Ignore symlink failure because of read-only file system, #3055
* Backport shortcut tests, #3064
* Fix #2979 redefinition of $SHELL variable, #3081
* Fix #3060 --clone root --copy exception, #3080


4.1.9 (2016-07-20)
==================

* Fix #3104, add global BINSTAR_TOKEN_PAT
* Handle failures in binstar_client more generally


4.1.8 (2016-07-12)
==================

* Fix #3004 UNAUTHORIZED for url (null binstar token), #3008
* Fix overwrite existing redirect shortcuts when symlinking envs, #3025
* Partially revert no default shortcuts, #3032, #3047


4.1.7 (2016-07-07)
==================

* Add msys2 channel to defaults on Windows, #2999
* Fix #2939 channel_alias issues; improve offline enforcement, #2964
* Fix #2970, #2974 improve handling of file:// URLs inside channel, #2976


4.1.6 (2016-07-01)
==================

* Slow down exp backoff from 1 ms to 100 ms factor, #2944
* Set max time on exp_backoff to ~6.5 sec,#2955
* Fix #2914 add/subtract from PATH; kill folder output text, #2917
* Normalize use of get_index behavior across clone/explicit, #2937
* Wrap root prefix check with normcase, #2938


4.1.5 (2016-06-29)
==================

* More conservative auto updates of conda #2900
* Fix some permissions errors with more aggressive use of move_path_to_trash, #2882
* Fix #2891 error if allow_other_channels setting is used, #2896
* Fix #2886, #2907 installing a tarball directly from the package cache, #2908
* Fix #2681, #2778 reverting #2320 lock behavior changes, #2915


4.1.4 (2016-06-27)
==================

* Fix #2846 revert the use of UNC paths; shorten trash filenames, #2859
* Fix exp backoff on Windows, #2860
* Fix #2845 URL for local file repos, #2862
* Fix #2764 restore full path var on win; create to CONDA_PREFIX env var, #2848
* Fix #2754 improve listing pip installed packages, #2873
* Change root prefix detection to avoid clobbering root activate scripts, #2880
* Address #2841 add lowest and highest priority indication to channel config output, #2875
* Add SYMLINK_CONDA to planned instructions, #2861
* Use CONDA_PREFIX, not CONDA_DEFAULT_ENV for activate.d, #2856
* Call scripts with redirect on win; more error checking to activate, #2852


4.1.3 (2016-06-23)
==================

* Ensure conda-env auto update, along with conda, #2772
* Make yaml booleans behave how everyone expects them to, #2784
* Use accept-encoding for repodata; prefer repodata.json to repodata.json.bz2, #2821
* Additional integration and regression tests, #2757, #2774, #2787
* Add offline mode to printed info; use offline flag when grabbing channels, #2813
* Show conda-env version in conda info, #2819
* Adjust channel priority superseded list, #2820
* Support epoch ! characters in command line specs, #2832
* Accept old default names and new ones when canonicalizing channel URLs #2839
* Push PATH, PS1 manipulation into shell scripts, #2796
* Fix #2765 broken source activate without arguments, #2806
* Fix standalone execution of install.py, #2756
* Fix #2810 activating conda environment broken with git bash on Windows, #2795
* Fix #2805, #2781 handle both file-based channels and explicit file-based URLs, #2812
* Fix #2746 conda create --clone of root, #2838
* Fix #2668, #2699 shell recursion with activate #2831


4.1.2 (2016-06-17)
==================

* Improve messaging for "downgrades" due to channel priority, #2718
* Support conda config channel append/prepend, handle duplicates, #2730
* Remove --shortcuts option to internal CLI code, #2723
* Fix an issue concerning space characters in paths in activate.bat, #2740
* Fix #2732 restore yes/no/on/off for booleans on the command line, #2734
* Fix #2642 tarball install on Windows, #2729
* Fix #2687, #2697 WindowsError when creating environments on Windows, #2717
* Fix #2710 link instruction in conda create causes TypeError, #2715
* Revert #2514, #2695, disabling of .netrc files, #2736
* Revert #2281 printing progress bar to terminal, #2707


4.1.1 (2016-06-16)
==================

* Add auto_update_conda config parameter, #2686
* Fix #2669 conda config --add channels can leave out defaults, #2670
* Fix #2703 ignore activate symlink error if links already exist, #2705
* Fix #2693 install duplicate packages with older version of Anaconda, #2701
* Fix #2677 respect HTTP_PROXY, #2695
* Fix #2680 broken fish integration, #2685, #2694
* Fix an issue with conda never exiting, #2689
* Fix #2688 explicit file installs, #2708
* Fix #2700 conda list UnicodeDecodeError, #2706


4.1.0 (2016-06-14)
==================

This release contains many small bug fixes for all operating systems, and a few
special fixes for Windows behavior.

Notable changes for all systems (Windows, macOS, and Linux)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* **Channel order now matters.** The most significant conda change is that
  when you add channels, channel order matters. If you have a list of channels
  in a .condarc file, conda installs the package from the first channel where
  it's available, even if it's available in a later channel with a higher
  version number.
* **No version downgrades.** Conda remove no longer performs version
  downgrades on any remaining packages that might be suggested to resolve
  dependency losses; the package will just be removed instead.
* **New YAML parser/emitter.** PyYAML is replaced with ruamel.yaml,
  which gives more robust control over yaml document use.
  `More on ruamel.yaml <http://yaml.readthedocs.io/en/latest/>`_
* **Shebang lines over 127 characters are now truncated (Linux, macOS only).**
  `Shebangs <https://en.wikipedia.org/wiki/Shebang_(Unix)>`_ are
  the first line of the many executable scripts that tell the operating
  system how to execute the program.  They start with ``#!``. Most OSes
  don't support these lines over 127 characters, so conda now checks
  the length and replaces the full interpreter path in long lines with
  ``/usr/bin/env``. When you're working in a conda environment that
  is deeply under many directories, or you otherwise have long paths
  to your conda environment, make sure you activate that environment
  now.
* **Changes to conda list command.** When looking for packages that
  aren’t installed with conda, conda list now examines the Python
  site-packages directory rather than relying on pip.
* **Changes to conda remove command.** The command  ``conda remove --all``
  now removes a conda environment without fetching information from a remote
  server on the packages in the environment.
* **Conda update can be turned off and on.** When turned off, conda will
  not update itself unless the user manually issues a conda update command.
  Previously conda updated any time a user updated or installed a package
  in the root environment. Use the option ``conda config set auto_update_conda false``.
* **Improved support for BeeGFS.** BeeGFS is a parallel cluster file
  system for performance and designed for easy installation and
  management. `More on BeeGFS <http://www.beegfs.com/content/documentation/>`_

Windows-only changes
^^^^^^^^^^^^^^^^^^^^

* **Shortcuts are no longer installed by default on Windows.** Shortcuts can
  now be installed with the ``--shortcuts`` option. Example 1: Install a shortcut
  to Spyder with ``conda install spyder --shortcut``. Note if you have Anaconda
  (not Miniconda), you already have this shortcut and Spyder. Example 2:
  Install the open source package named ``console_shortcut``. When you click
  the shortcut icon, a terminal window will open with the environment
  containing the ``console_shortcut`` package already activated. ``conda install
  console_shortcut --shortcuts``
* **Skip binary replacement on Windows.** Linux & macOS have binaries that
  are coded with library locations, and this information must sometimes be
  replaced for relocatability, but Windows does not generally embed prefixes
  in binaries, and was already relocatable. We skip binary replacement on
  Windows.

Complete list:

* Clean up activate and deactivate scripts, moving back to conda repo, #1727, #2265, #2291, #2473, #2501, #2484
* Replace pyyaml with ruamel_yaml, #2283, #2321
* Better handling of channel collisions, #2323, #2369 #2402, #2428
* Improve listing of pip packages with conda list, #2275
* Re-license progressbar under BSD 3-clause, #2334
* Reduce the amount of extraneous info in hints, #2261
* Add --shortcuts option to install shortcuts on windows, #2623
* Skip binary replacement on windows, #2630
* Don't show channel urls by default in conda list, #2282
* Package resolution and solver tweaks, #2443, #2475, #2480
* Improved version & build matching, #2442, #2488
* Print progress to the terminal rather than stdout, #2281
* Verify version specs given on command line are valid, #2246
* Fix for try_write function in case of odd permissions, #2301
* Fix a conda search --spec error, #2343
* Update User-Agent for conda connections, #2347
* Remove some dead code paths, #2338, #2374
* Fixes a thread safety issue with http requests, #2377, #2383
* Manage BeeGFS hard-links non-POSIX configuration, #2355
* Prevent version downgrades during removes, #2394
* Fix conda info --json, #2445
* Truncate shebangs over 127 characters using /usr/bin/env, #2479
* Extract packages to a temporary directory then rename, #2425, #2483
* Fix help in install, #2460
* Fix re-install bug when sha1 differs, #2507
* Fix a bug with file deletion, #2499
* Disable .netrc files, #2514
* Dont fetch index on remove --all, #2553
* Allow track_features to be a string *or* a list in .condarc, #2541
* Fix #2415 infinite recursion in invalid_chains, #2566
* Allow channel_alias to be different than binstar, #2564


4.0.11 (2016-07-09)
===================

* Allow auto_update_conda from sysrc, #3015 via #3021


4.0.10 (2016-06-29)
===================

* Fix #2846 revert the use of UNC paths; shorten trash filenames, #2859 via #2878
* Fix some permissions errors with more aggressive use of move_path_to_trash, #2882 via #2894


4.0.9 (2016-06-15)
==================

* Add auto_update_conda config parameter, #2686


4.0.8 (2016-06-03)
==================

* Fix a potential problem with moving files to trash, #2587


4.0.7 (2016-05-26)
==================

* Workaround for boto bug, #2380


4.0.6 (2016-05-11)
==================

* Log "custom" versions as updates rather than downgrades, #2290
* Fixes a TypeError exception that can occur on install/update, #2331
* Fixes an error on Windows removing files with long path names, #2452


4.0.5 (2016-03-16)
==================

* Improved help documentation for install, update, and remove, #2262
* Fixes #2229 and #2250 related to conda update errors on Windows, #2251
* Fixes #2258 conda list for pip packages on Windows, #2264


4.0.4 (2016-03-10)
==================

* Revert #2217 closing request sessions, #2233


4.0.3 (2016-03-10)
==================

* Adds a `conda clean --all` feature, #2211
* Solver performance improvements, #2209
* Fixes conda list for pip packages on windows, #2216
* Quiets some logging for package downloads under Python 3, #2217
* More urls for `conda list --explicit`, #1855
* Prefer more "latest builds" for more packages, #2227
* Fixes a bug with dependency resolution and features, #2226


4.0.2 (2016-03-08)
==================

* Fixes track_features in ~/.condarc being a list, see also #2203
* Fixes incorrect path in lock file error #2195
* Fixes issues with cloning environments, #2193, #2194
* Fixes a strange interaction between features and versions, #2206
* Fixes a bug in low-level SAT clause generation creating a preference for older versions, #2199


4.0.1 (2016-03-07)
==================

* Fixes an install issue caused by md5 checksum mismatches, #2183
* Remove auxlib build dependency, #2188


4.0.0 (2016-03-04)
==================

* The solver has been retooled significantly. Performance should be improved in most circumstances, and a number of issues involving feature conflicts should be resolved.

* `conda update <package>` now handles depedencies properly according to the setting of the "update_deps" configuration:

    --update-deps: conda will also update any dependencies as needed to install the latest verison of the requrested packages.  The minimal set of changes required to achieve this is sought.

    --no-update-deps: conda will update the packages *only* to the extent that no updates to the dependencies are required

  The previous behavior, which would update the packages without regard to their dependencies, could result in a broken configuration, and has been removed.

* Conda finally has an official logo.

* Fix `conda clean --packages` on Windows, #1944

* Conda sub-commands now support dashes in names, #1840


3.19.3 (2016-02-19)
===================

* Fix critical issue, see #2106


3.19.2 (2016-02-19)
===================

* Add basic activate/deactivate, conda activate/deactivate/ls for fish, see #545
* Remove error when CONDA_FORCE_32BIT is set on 32-bit systems, #1985
* Suppress help text for --unknown option, #2051
* Fix issue with conda create --clone post-link scripts, #2007
* Fix a permissions issue on windows, #2083


3.19.1 (2016-02-01)
===================

* Resolve.py: properly escape periods in version numbers, #1926
* Support for pinning Lua by default, #1934
* Remove hard-coded test URLs, a module cio_test is now expected when CIO_TEST is set


3.19.0 (2015-12-17)
===================

* OpenBSD 5.x support, #1891
* improve install CLI to make Miniconda -f work, #1905


3.18.9 (2015-12-10)
===================

* Allow chaning default_channels (only applies to "system" condarc), from from CLI, #1886
* Improve default for --show-channel-urls in conda list, #1900


3.18.8 (2015-12-03)
===================

* Always attempt to delete files in rm_rf, #1864


3.18.7 (2015-12-02)
===================

* Simplify call to menuinst.install()
* Add menuinst as dependency on Windows
* Add ROOT_PREFIX to post-link (and pre_unlink) environment


3.18.6 (2015-11-19)
===================

* Improve conda clean when user lacks permissions, #1807
* Make show_channel_urls default to True, #1771
* Cleaner write tests, #1735
* Fix documentation, #1709
* Improve conda clean when directories don't exist, #1808


3.18.5 (2015-11-11)
===================

* Fix bad menuinst exception handling, #1798
* Add workaround for unresolved dependencies on Windows


3.18.4 (2015-11-09)
===================

* Allow explicit file to contain MD5 hashsums
* Add --md5 option to "conda list --explicit"
* Stop infinite recursion during certain resolve operations, #1749
* Add dependencies even if strictness == 3, #1766


3.18.3 (2015-10-15)
===================

* Added a pruning step for more efficient solves, #1702
* Disallow conda-env to be installed into non-root environment
* Improve error output for bad command input, #1706
* Pass env name and setup cmd to menuinst, #1699


3.18.2 (2015-10-12)
===================

* Add "conda list --explicit" which contains the URLs of all conda packages to be installed, and can used with the install/create --file option, #1688
* Fix a potential issue in conda clean
* Avoid issues with LookupErrors when updating Python in the root environment on Windows
* Don't fetch the index from the network with conda remove
* When installing conda packages directly, "conda install <pkg>.tar.bz2", unlink any installed package with that name, not just the installed one
* Allow menu items to be installed in non-root env, #1692


3.18.1 (2015-09-28)
===================

* Fix: removed reference to win_ignore_root in plan module


3.18.0 (2015-09-28)
===================

* Allow Python to be updated in root environment on Windows, #1657
* Add defaults to specs after getting pinned specs (allows to pin a different version of Python than what is installed)
* Show what older versions are in the solutions in the resolve debug log
* Fix some issues with Python 3.5
* Respect --no-deps when installing from .tar or .tar.bz2
* Avoid infinite recursion with NoPackagesFound and conda update --all --file
* Fix conda update --file
* Toposort: Added special case to remove 'pip' dependency from 'Python'
* Show dotlog messages during hint generation with --debug
* Disable the max_only heuristic during hint generation
* New version comparison algorithm, which consistently compares any version string, and better handles version strings using things like alpha, beta, rc, post, and dev. This should remove any inconsistent version comparison that would lead to conda installing an incorrect version.
* Use the trash in rm_rf, meaning more things will get the benefit of the trash system on Windows
* Add the ability to pass the --file argument multiple times
* Add conda upgrade alias for conda update
* Add update_dependencies condarc option and --update-deps/--no-update-deps command line flags
* Allow specs with conda update --all
* Add --show-channel-urls and --no-show-channel-urls command line options
* Add always_copy condarc option
* Conda clean properly handles multiple envs directories. This breaks backwards compatibility with some of the --json output. Some of the old --json keys are kept for backwards compatibility.


3.17.0 (2015-09-11)
===================

* Add windows_forward_slashes option to walk_prefix(), see #1513
* Add ability to set CONDA_FORCE_32BIT environment variable, it should should only be used when running conda-build, #1555
* Add config option to makes the Python dependency on pip optional, #1577
* Fix an UnboundLocalError
* Print note about pinned specs in no packages found error
* Allow wildcards in AND-connected version specs
* Print pinned specs to the debug log
* Fix conda create --clone with create_default_packages
* Give a better error when a proxy isn't found for a given scheme
* Enable running 'conda run' in offline mode
* Fix issue where hardlinked cache contents were being overwritten
* Correctly skip packages whose dependencies can't be found with conda update --all
* Use clearer terminology in -m help text.
* Use splitlines to break up multiple lines throughout the codebase
* Fix AttributeError with SSLError


3.16.0 (2015-08-10)
===================

* Rename binstar -> Anaconda, see #1458
* Fix --use-local when the conda-bld directory doesn't exist
* Fixed --offline option when using "conda create --clone", see #1487
* Don't mask recursion depth errors
* Add conda search --reverse-dependency
* Check whether hardlinking is available before linking when using "Python install.py --link" directly, see #1490
* Don't exit nonzero when installing a package with no dependencies
* Check which features are installed in an environment via track_features, not features
* Set the verify flag directly on CondaSession (fixes conda skeleton not respecting the ssl_verify option)


3.15.1 (2015-07-23)
===================

* Fix conda with older versions of argcomplete
* Restore the --force-pscheck option as a no-op for backwards compatibility


3.15.0 (2015-07-22)
===================

* Sort the output of conda info package correctly
* Enable tab completion of conda command extensions using argcomplete. Command extensions that import conda should use conda.cli.conda_argparse.ArgumentParser instead of argparse.ArgumentParser. Otherwise, they should enable argcomplete completion manually.
* Allow psutil and pycosat to be updated in the root environment on Windows
* Remove all mentions of pscheck. The --force-pscheck flag has been removed.
* Added support for S3 channels
* Fix color issues from pip in conda list on Windows
* Add support for other machine types on Linux, in particular ppc64le
* Add non_x86_linux_machines set to config module
* Allow ssl_verify to accept strings in addition to boolean values in condarc
* Enable --set to work with both boolean and string values


3.14.1 (2015-06-29)
===================

* Make use of Crypto.Signature.PKCS1_PSS module, see #1388
* Note when features are being used in the unsatisfiable hint


3.14.0 (2015-06-16)
===================

* Add ability to verify signed packages, see #1343 (and conda-build #430)
* Fix issue when trying to add 'pip' dependency to old Python packages
* Provide option "conda info --unsafe-channels" for getting unobscured channel list, #1374


3.13.0 (2015-06-04)
===================

* Avoid the Windows file lock by moving files to a trash directory, #1133
* Handle env dirs not existing in the Environments completer
* Rename binstar.org -> anaconda.org, see #1348
* Speed up 'source activate' by ~40%


3.12.0 (2015-05-05)
===================

* Correctly allow conda to update itself
* Print which file leads to the "unable to remove file" error on Windows
* Add support for the no_proxy environment variable, #1171
* Add a much faster hint generation for unsatisfiable packages, which is now always enabled (previously it would not run if there were more than ten specs). The new hint only gives one set of conflicting packages, rather than all sets, so multiple passes may be necessary to fix such issues
* Conda extensions that import conda should use conda.cli.conda_argparser.ArgumentParser instead of argparse.ArgumentParser to conform to the conda help guidelines (e.g., all help messages should be capitalized with periods, and the options should be preceded by "Options:" for the sake of help2man).
* Add confirmation dialog to conda remove. Fixes conda remove --dry-run.

3.11.0 (2015-04-22)
===================

* Fix issue where forced update on Windows could cause a package to break
* Remove detection of running processes that might conflict
* Deprecate --force-pscheck (now a no-op argument)
* Make conda search --outdated --names-only work, fixes #1252
* Handle the history file not having read or write permissions better
* Make multiple package resolutions warning easier to read
* Add --full-name to conda list
* Improvements to command help


2015-04-06   3.10.1:
====================

* Fix logic in @memoized for unhashable args
* restored json cache of repodata, see #1249
* hide binstar tokens in conda info --json
* handle CIO_TEST='2 '
* always find the solution with minimal number of packages, even if there are many solutions
* allow comments at the end of the line in requirement files
* don't update the progressbar until after the item is finished running
* Add conda/<version> to HTTP header User-Agent string


2015-03-12   3.10.0:
====================

* change default repo urls to be https
* Add --offline to conda search
* Add --names-only and --full-name to conda search
* Add tab completion for packages to conda search


2015-02-24   3.9.1:
===================

* pscheck: check for processes in the current environment, see #1157
* don't write to the history file if nothing has changed, see #1148
* conda update --all installs packages without version restrictions (except for Python), see #1138
* conda update --all ignores the anaconda metapackage, see #1138
* use forward slashes for file urls on Windows
* don't symlink conda in the root environment from activate
* use the correct package name in the progress bar info
* use json progress bars for unsatisfiable dependencies hints
* don't let requests decode gz files when downloaded


2015-02-16   3.9.0:
===================

* remove (de)activation scripts from conda, those are now in conda-env
* pip is now always added as a Python dependency
* allow conda to be installed into environments which start with _
* Add argcomplete tab completion for environments with the -n flag, and for package names with install, update, create, and remove


2015-02-03   3.8.4:
===================

* copy (de)activate scripts from conda-env
* Add noarch (sub) directory support


2015-01-28   3.8.3:
===================

* simplified how ROOT_PREFIX is obtained in (de)activate


2015-01-27   3.8.2:
===================

* Add conda clean --source-cache to clean the conda build source caches
* Add missing quotes in (de)activate.bat, fixes problem in Windows when conda is installed into a directory with spaces
* Fix conda install --copy


2015-01-23   3.8.1:
===================

* Add missing utf-8 decoding, fixes Python 3 bug when icondata to json file


2015-01-22   3.8.0:
===================

* move active script into conda-env, which is now a new dependency
* load the channel urls in the correct order when using concurrent.futures
* Add optional 'icondata' key to json files in conda-meta directory, which contain the base64 encoded png file or the icon
* remove a debug print statement


2014-12-18   3.7.4:
===================

* Add --offline option to install, create, update and remove commands, and also add ability to set "offline: True" in condarc file
* Add conda uninstall as alias for conda remove
* Add conda info --root
* Add conda.pip module
* Fix CONDARC pointing to non-existing file, closes issue #961
* make update -f work if the package is already up-to-date
* Fix possible TypeError when printing an error message
* link packages in topologically sorted order (so that pre-link scripts can assume that the dependencies are installed)
* Add --copy flag to install
* prevent the progressbar from crashing conda when fetching in some situations


3.7.3 (2014-11-05)
===================

* Conda install from a local conda package (or a tar fill which contains conda packages), will now also install the dependencies listed by the installed packages.
* Add SOURCE_DIR environment variable in pre-link subprocess
* Record all created environments in ~/.conda/environments.txt


3.7.2 (2014-10-31)
==================

* Only show the binstar install message once
* Print the fetching repodata dot after the repodata is fetched
* Write the install and remove specs to the history file
* Add '-y' as an alias to '--yes'
* The `--file` option to conda config now defaults to os.environ.get('CONDARC')
* Some improvements to documentation (--help output)
* Add user_rc_path and sys_rc_path to conda info --json
* Cache the proxy username and password
* Avoid warning about conda in pscheck
* Make ~/.conda/envs the first user envs dir


3.7.1 (2014-10-07)
==================

* Improve error message for forgetting to use source with activate and deactivate, see issue #601
* Don't allow to remove the current environment, see issue #639
* Don't fail if binstar_client can't be imported for other reasons, see issue #925
* Allow spaces to be contained in conda run
* Only show the conda install binstar hint if binstar is not installed
* Conda info package_spec now gives detailed info on packages. conda info path has been removed, as it is duplicated by conda package -w path.


3.7.0 (2014-09-19)
==================

* Faster algorithm for --alt-hint
* Don't allow channel_alias with allow_other_channels: false if it is set in the system .condarc
* Don't show long "no packages found" error with update --all
* Automatically add the Binstar token to urls when the binstar client is installed and logged in
* Carefully avoid showing the binstar token or writing it to a file
* Be more careful in conda config about keys that are the wrong type
* Don't expect directories starting with conda- to be commands
* No longer recommend to run conda init after pip installing conda. A pip installed conda will now work without being initialized to create and manage other environments
* The rm function on Windows now works around access denied errors
* Fix channel urls now showing with conda list with show_channel_urls set to true


3.6.4 (2014-09-08)
==================

* Fix removing packages that aren't in the channels any more
* Pretties output for --alt-hint


3.6.3 (2014-09-04)
==================

* Skip packages that can't be found with update --all
* Add --use-local to search and remove
* Allow --use-local to be used along with -c (--channels) and --override-channels. --override-channels now requires either -c or --use-local
* Allow paths in has_prefix to be quoted, to allow for spaces in paths on Windows
* Retain Linux/macOS style path separators for prefixes in has_prefix on Windows (if the placeholder path uses /, replace it with a path that uses /, not \\)
* Fix bug in --use-local due to API changes in conda-build
* Include user site directories in conda info -s
* Make binary has_prefix replacement work with spaces after the prefix
* Make binary has_prefix replacement replace multiple occurrences of the placeholder in the same null-terminated string
* Don't show packages from other platforms as installed or cached in conda search
* Be more careful about not warning about conda itself in pscheck
* Use a progress bar for the unsatisfiable packages hint generation
* Don't use TemporaryFile in try_write, as it is too slow when it fails
* Ignore InsecureRequestWarning when ssl_verify is False
* Conda remove removes features tracked by removed packages in track_features


3.6.2 (2014-08-20)
==================

* Add --use-index-cache to conda remove
* Fix a bug where features (like mkl) would be selected incorrectly
* Use concurrent.future.ThreadPool to fetch package metadata asynchronously in Python 3.
* Do the retries in rm_rf on every platform
* Use a higher cutoff for package name misspellings
* Allow changing default channels in "system" .condarc


3.6.1 (2014-08-13)
==================

* Add retries to download in fetch module
* Improved error messages for missing packages
* More robust rm_rf on Windows
* Print multiline help for subcommands correctly


3.6.0 (2014-08-11)
==================

* Correctly check if a package can be hard-linked if it isn't extracted yet
* Change how the package plan is printed to better show what is new, updated, and downgraded
* Use suggest_normalized_version in the resolve module. Now versions like 1.0alpha that are not directly recognized by verlib's NormalizedVersion are supported better
* Conda run command, to run apps and commands from packages
* More complete --json API. Every conda command should fully support --json output now.
* Show the conda_build and requests versions in conda info
* Include packages from setup.py develop in conda list (with use_pip)
* Raise a warning instead of dying when the history file is invalid
* Use urllib.quote on the proxy password
* Make conda search --outdated --canonical work
* Pin the Python version during conda init
* Fix some metadata that is written for Python during conda init
* Allow comments in a pinned file
* Allow installing and updating menuinst on Windows
* Allow conda create with both --file and listed packages
* Better handling of some nonexistent packages
* Fix command line flags in conda package
* Fix a bug in the ftp adapter


3.5.5 (2014-06-10)
==================

* Remove another instance pycosat version detection, which fails on Windows, see issue #761


3.5.4 (2014-06-10)
==================

* Remove pycosat version detection, which fails on Windows, see issue #761


3.5.3 (2014-06-09)
==================

* Fix conda update to correctly not install packages that are already up-to-date
* Always fail with connection error in download
* The package resolution is now much faster and uses less memory
* Add ssl_verify option in condarc to allow ignoring SSL certificate verification, see issue #737


3.5.2 (2014-05-27)
==================

* Fix bug in activate.bat and deactivate.bat on Windows


3.5.1 (2014-05-26)
==================

* Fix proxy support - conda now prompts for proxy username and password again
* Fix activate.bat on Windows with spaces in the path
* Update optional psutil dependency was updated to psutil 2.0 or higher


3.5.0 (2014-05-15)
==================

* Replace use of urllib2 with requests. requests is now a hard dependency of conda.
* Add ability to only allow system-wise specified channels
* Hide binstar from output of conda info


3.4.3 (2014-05-05)
==================

* Allow prefix replacement in binary files, see issue #710
* Check if creating hard link is possible and otherwise copy, during install
* Allow circular dependencies


3.4.2 (2014-04-21)
==================

* Conda clean --lock: skip directories that don't exist, fixes #648
* Fixed empty history file causing crash, issue #644
* Remove timezone information from history file, fixes issue #651
* Fix PackagesNotFound error for missing recursive dependencies
* Change the default for adding cache from the local package cache - known is now the default and the option to use index metadata from the local package cache is --unknown
* Add --alt-hint as a method to get an alternate form of a hint for unsatisfiable packages
* Add conda package --ls-files to list files in a package
* Add ability to pin specs in an environment. To pin a spec, add a file called pinned to the environment's conda-meta directory with the specs to pin. Pinned specs are always kept installed, unless the --no-pin flag is used.
* Fix keyboard interrupting of external commands. Now keyboard interrupting conda build correctly removes the lock file
* Add no_link ability to conda, see issue #678


3.4.1 (2014-04-07)
==================

* Always use a pkgs cache directory associated with an envs directory, even when using -p option with an arbitrary a prefix which is not inside an envs dir
* Add setting of PYTHONHOME to conda info --system
* Skip packages with bad metadata

3.4.0 (2014-04-02)
==================

* Added revision history to each environment:

  - conda list --revisions

  - conda install --revision

  - log is stored in conda-meta/history

* Allow parsing pip-style requirement files with --file option and in command line arguments, e.g. conda install 'numpy>=1.7', issue #624

* Fix error message for --file option when file does not exist

* Allow DEFAULTS in CONDA_ENVS_PATH, which expands to the defaults settings, including the condarc file

* Don't install a package with a feature (like mkl) unless it is specifically requested (i.e., that feature is already enabled in that environment)

* Add ability to show channel URLs when displaying what is going to be downloaded by setting "show_channel_urls: True" in condarc

* Fix the --quiet option

* Skip packages that have dependencies that can't be found

3.3.2 (2014-03-24)
==================

* Fix the --file option
* Check install arguments before fetching metadata
* Fix a printing glitch with the progress bars
* Give a better error message for conda clean with no arguments
* Don't include unknown packages when searching another platform


3.3.1 (2014-03-19)
==================

* Fix setting of PS1 in activate.
* Add conda update --all.
* Allow setting CONDARC=' ' to use no condarc.
* Add conda clean --packages.
* Don't include bin/conda, bin/activate, or bin/deactivate in conda package.


3.3.0 (2014-03-18)
==================

* Allow new package specification, i.e. ==, >=, >, <=, <, != separated by ',' for example: >=2.3,<3.0
* Add ability to disable self update of conda, by setting "self_update: False" in .condarc
* Try installing packages using the old way of just installing the maximum versions of things first. This provides a major speedup of solving the package specifications in the cases where this scheme works.
* Don't include Python=3.3 in the specs automatically for the Python 3 version of conda.  This allows you to do "conda create -n env package" for a package that only has a Python 2 version without specifying "Python=2". This change has no effect in Python 2.
* Automatically put symlinks to conda, activate, and deactivate in each environment on Linux and macOS.
* On Linux and macOS, activate and deactivate now remove the root environment from the PATH. This should prevent "bleed through" issues with commands not installed in the activated environment but that are installed in the root environment. If you have "setup.py develop" installed conda on Linux or macOS, you should run this command again, as the activate and deactivate scripts have changed.
* Begin work to support Python 3.4.
* Fix a bug in version comparison
* Fix usage of sys.stdout and sys.stderr in environments like pythonw on Windows where they are nonstandard file descriptors.


3.2.1 (2014-03-12)
==================

* Fix installing packages with irrational versions
* Fix installation in the api
* Use a logging handler to print the dots


3.2.0 (2014-03-11)
==================

* Print dots to the screen for progress
* Move logic functions from resolve to logic module


3.2.0a1 (2014-03-07)
====================

* Conda now uses pseudo-boolean constraints in the SAT solver. This allows it to search for all versions at once, rather than only the latest (issue #491).
* Conda contains a brand new logic submodule for converting pseudo-boolean constraints into SAT clauses.

3.1.1 (2014-03-07)
==================

* Check if directory exists, fixed issue #591


3.1.0 (2014-03-07)
==================

* Local packages in cache are now added to the index, this may be disabled by using the --known option, which only makes conda use index metadata from the known remote channels
* Add --use-index-cache option to enable using cache of channel index files
* Fix ownership of files when installing as root on Linux
* Conda search: add '.' symbol for extracted (cached) packages


3.0.6 (2014-02-20)
==================

* Fix 'conda update' taking build number into account


3.0.5 (2014-02-17)
==================

* Allow packages from create_default_packages to be overridden from the command line
* Fixed typo install.py, issue #566
* Try to prevent accidentally installing into a non-root conda environment


3.0.4 (2014-02-14)
==================

* Conda update: don't try to update packages that are already up-to-date


3.0.3 (2014-02-06)
==================

* Improve the speed of clean --lock
* Some fixes to conda config
* More tests added
* Choose the first solution rather than the last when there are more than one, since this is more likely to be the one you want.


3.0.2 (2014-02-03)
==================

* Fix detection of prefix being writable


3.0.1 (2014-01-31)
==================

* Bug: not having track_features in condarc now uses default again
* Improved test suite
* Remove numpy version being treated special in plan module
* If the post-link.(bat|sh) fails, don't treat it as though it installed, i.e. it is not added to conda-meta
* Fix activate if CONDA_DEFAULT_ENV is invalid
* Fix conda config --get to work with list keys again
* Print the total download size
* Fix a bug that was preventing conda from working in Python 3
* Add ability to run pre-link script, issue #548


3.0.0 (2014-01-24)
==================

* Removed build, convert, index, and skeleton commands, which are now part of the conda-build project: https://github.com/conda/conda-build
* Limited pip integration to `conda list`, that means `conda install` no longer calls `pip install` # !!!
* Add ability to call sub-commands named 'conda-x'
* The -c flag to conda search is now shorthand for --channel, not --canonical (this is to be consistent with other conda commands)
* Allow changing location of .condarc file using the CONDARC environment variable
* Conda search now shows the channel that the package comes from
* Conda search has a new --platform flag for searching for packages in other platforms.
* Remove condarc warnings: issue #526#issuecomment-33195012


2.3.1 (2014-01-17)
==================

* Add ability create info/no_softlink
* Add conda convert command to convert non-platform-dependent packages from one platform to another (experimental)
* unify create, install, and update code. This adds many features to create and update that were previously only available to install. A backwards incompatible change is that conda create -f now means --force, not --file.


2.3.0 (2014-01-16)
==================

* Automatically prepend http://conda.binstar.org/ (or the value of channel_alias in the .condarc file) to channels whenever the channel is not a URL or the word 'defaults or 'system'
* Recipes made with the skeleton pypi command will use setuptools instead of distribute
* Re-work the setuptools dependency and entry_point logic so that non console_script entry_points for packages with a dependency on setuptools will get correct build script with conda skeleton pypi
* Add -m, --mkdir option to conda install
* Add ability to disable soft-linking


2.2.8 (2014-01-06)
==================

* Add check for chrpath (on Linux) before build is started, see issue #469
* Conda build: fixed ELF headers not being recognized on Python 3
* Fixed issues: #467, #476


2.2.7 (2014-01-02)
==================

* Fixed bug in conda build related to lchmod not being available on all platforms


2.2.6 (2013-12-31)
==================

* Fix test section for automatic recipe creation from pypi using --build-recipe
* Minor Py3k fixes for conda build on Linux
* Copy symlinks as symlinks, issue #437
* Fix explicit install (e.g. from output of `conda list -e`) in root env
* Add pyyaml to the list of packages which can not be removed from root environment
* Fixed minor issues: #365, #453


2.2.5 (2013-12-17)
==================

* Conda build: move broken packages to conda-bld/broken
* Conda config: automatically Add the 'defaults' channel
* Conda build: improve error handling for invalid recipe directory
* Add ability to set build string, issue #425
* Fix LD_RUN_PATH not being set on Linux under Python 3, see issue #427, thanks peter1000


2.2.4 (2013-12-10)
==================

* Add support for execution with the -m switch (issue #398), i.e. you can execute conda also as: Python -m conda
* Add a deactivate script for windows
* Conda build adds .pth-file when it encounters an egg (TODO)
* Add ability to preserve egg directory when building using build/preserve_egg_dir: True
* Allow track_features in ~/.condarc
* Allow arbitrary source, issue #405
* Fixed minor issues: #393, #402, #409, #413


2.2.3 (2013-12-03)
==================

* Add "foreign mode", i.e. disallow install of certain packages when using a "foreign" Python, such as the system Python
* Remove activate/deactivate from source tarball created by sdist.sh, in order to not overwrite activate script from virtualenvwrapper


2.2.2 (2013-11-27)
==================

* Remove ARCH environment variable for being able to change architecture
* Add PKG_NAME, PKG_VERSION to environment when running build.sh, .<name>-post-link.sh and .<name>-pre-unlink.sh


2.2.1 (2013-11-15)
==================

* Minor fixes related to make conda pip installable
* Generated conda meta-data missing 'files' key, fixed issue #357


2.2.0 (2013-11-14)
==================


* Add conda init command, to allow installing conda via pip
* Fix prefix being replaced by placeholder after conda build on Linux and macOS
* Add 'use_pip' to condarc configuration file
* Fixed activate on Windows to set CONDA_DEFAULT_ENV
* Allow setting "always_yes: True" in condarc file, which implies always using the --yes option whenever asked to proceed


2.1.0 (2013-11-07)
==================

* Fix rm_egg_dirs so that the .egg_info file can be a zip file
* Improve integration with pip
  * Conda list now shows pip installed packages
  * Conda install will try to install via "pip install" if no conda package is available (unless --no-pip is provided)
  * Conda build has a new --build-recipe option which will create a recipe (stored in <root>/conda-recipes) from pypi then build a conda package (and install it)
  * Pip list and pip install only happen if pip is installed
* Enhance the locking mechanism so that conda can call itself in the same process.


2.0.4 (2013-11-04)
==================

* Ensure lowercase name when generating package info, fixed issue #329
* On Windows, handle the .nonadmin files


2.0.3 (2013-10-28)
==================

* Update bundle format
* Fix bug when displaying packages to be downloaded (thanks Crystal)


2.0.2 (2013-10-27)
==================

* Add --index-cache option to clean command, see issue #321
* Use RPATH (instead of RUNPATH) when building packages on Linux


2.0.1 (2013-10-23)
==================

* Add --no-prompt option to conda skeleton pypi
* Add create_default_packages to condarc (and --no-default-packages option to create command)


2.0.0 (2013-10-01)
==================

* Added user/root mode and ability to soft-link across filesystems
* Added create --clone option for copying local environments
* Fixed behavior when installing into an environment which does not exist yet, i.e. an error occurs
* Fixed install --no-deps option
* Added --export option to list command
* Allow building of packages in "user mode"
* Regular environment locations now used for build and test
* Add ability to disallow specification names
* Add ability to read help messages from a file when install location is RO
* Restore backwards compatibility of share/clone for conda-api
* Add new conda bundle command and format
* Pass ARCH environment variable to build scripts
* Added progress bar to source download for conda build, issue #230
* Added ability to use url instead of local file to conda install --file and conda create --file options


1.9.1 (2013-09-06)
==================

* Fix bug in new caching of repodata index


1.9.0 (2013-09-05)
==================

* Add caching of repodata index
* Add activate command on Windows
* Add conda package --which option, closes issue 163
* Add ability to install file which contains multiple packages, issue 256
* Move conda share functionality to conda package --share
* Update documentation
* Improve error messages when external dependencies are unavailable
* Add implementation for issue 194: post-link or pre-unlink may append to a special file ${PREFIX}/.messages.txt for messages, which is display to the user's console after conda completes all actions
* Add conda search --outdated option, which lists only installed packages for which newer versions are available
* Fixed numerous Py3k issues, in particular with the build command


1.8.2 (2013-08-16)
==================

* Add conda build --check option
* Add conda clean --lock option
* Fixed error in recipe causing conda traceback, issue 158
* Fixes conda build error in Python 3, issue 238
* Improve error message when test command fails, as well as issue 229
* Disable Python (and other packages which are used by conda itself) to be updated in root environment on Windows
* Simplified locking, in particular locking should never crash conda when files cannot be created due to permission problems


1.8.1 (2013-08-07)
==================

* Fixed conda update for no arguments, issue 237
* Fix setting prefix before calling should_do_win_subprocess() part of issue 235
* Add basic subversion support when building
* Add --output option to conda build

1.8.0 (2013-07-31)
==================

* Add Python 3 support (thanks almarklein)
* Add Mercurial support when building from source (thanks delicb)
* Allow Python (and other packages which are used by conda itself) to be updated in root environment on Windows
* Add conda config command
* Add conda clean command
* Removed the conda pip command
* Improve locking to be finer grained
* Made activate/deactivate work with zsh (thanks to mika-fischer)
* Allow conda build to take tarballs containing a recipe as arguments
* Add PKG_CONFIG_PATH to build environment variables
* Fix entry point scripts pointing to wrong Python when building Python 3 packages
* Allow source/sha1 in meta.yaml, issue 196
* More informative message when there are unsatisfiable package specifications
* Ability to set the proxy urls in condarc
* Conda build asks to upload to binstar. This can also be configured by changing binstar_upload in condarc.
* Basic tab completion if the argcomplete package is installed and eval "$(register-Python-argcomplete conda)" is added to the bash profile.


1.7.2 (2013-07-02)
==================

* Fixed conda update when packages include a post-link step which was caused by subprocess being lazily imported, fixed by 0d0b860
* Improve error message when 'chrpath' or 'patch' is not installed and needed by build framework
* Fixed sharing/cloning being broken (issue 179)
* Add the string LOCKERROR to the conda lock error message


1.7.1 (2013-06-21)
==================

* Fix "executable" not being found on Windows when ending with .bat when launching application
* Give a better error message from when a repository does not exist


1.7.0 (2013-06-20)
==================

* Allow ${PREFIX} in app_entry
* Add binstar upload information after conda build finishes


1.7.0a2 (2013-06-20)
====================

* Add global conda lock file for only allowing one instance of conda to run at the same time
* Add conda skeleton command to create recipes from PyPI
* Add ability to run post-link and pre-unlink script


1.7.0a1 (2013-06-13)
====================

* Add ability to build conda packages from "recipes", using the conda build command, for some examples, see: https://github.com/ContinuumIO/conda-recipes
* Fixed bug in conda install --force
* Conda update command no longer uses anaconda as default package name
* Add proxy support
* Added application API to conda.api module
* Add -c/--channel and --override-channels flags (issue 121).
* Add default and system meta-channels, for use in .condarc and with -c (issue 122).
* Fixed ability to install ipython=0.13.0 (issue 130)


1.6.0 (2013-06-05)
==================

* Update package command to reflect changes in repodata
* Fixed refactoring bugs in share/clone
* Warn when Anaconda processes are running on install in Windows (should fix most permissions errors on Windows)


1.6.0rc2 (2013-05-31)
=====================

* Conda with no arguments now prints help text (issue 111)
* Don't allow removing conda from root environment
* Conda update Python no longer updates to Python 3, also ensure that conda itself is always installed into the root environment (issue 110)


1.6.0rc1 (2013-05-30)
=====================

* Major internal refactoring
* Use new "depends" key in repodata
* Uses pycosat to solve constraints more efficiently
* Add hard-linking on Windows
* Fixed linking across filesystems (issue 103)
* Add conda remove --features option
* Added more tests, in particular for new dependency resolver
* Add internal DSL to perform install actions
* Add package size to download preview
* Add conda install --force and --no-deps options
* Fixed conda help command
* Add conda remove --all option for removing entire environment
* Fixed source activate on systems where sourcing a gives "bash" as $0
* Add information about installed versions to conda search command
* Removed known "locations"
* Add output about installed packages when update and install do nothing
* Changed default when prompted for y/n in CLI to yes


1.5.2 (2013-04-29)
==================

* Fixed issue 59: bad error message when pkgs dir is not writable


1.5.1 (2013-04-19)
==================

* Fixed issue 71 and (73 duplicate): not being able to install packages starting with conda (such as 'conda-api')
* Fixed issue 69 (not being able to update Python / NumPy)
* Fixed issue 76 (cannot install mkl on OSX)


1.5.0 (2013-03-22)
==================

* Add conda share and clone commands
* Add (hidden) --output-json option to clone, share and info commands to support the conda-api package
* Add repo sub-directory type 'linux-armv6l'


1.4.6 (2013-03-12)
==================

* Fixed channel selection (issue #56)


1.4.5 (2013-03-11)
==================

* Fix issue #53 with install for meta packages
* Add -q/--quiet option to update command


1.4.4 (2013-03-09)
==================

* Use numpy 1.7 as default on all platfroms


1.4.3 (2013-03-09)
==================

* Fixed bug in conda.builder.share.clone_bundle()


1.4.2 (2013-03-08)
==================

* Feature selection fix for update
* Windows: don't allow linking or unlinking Python from the root environment because the file lock, see issue #42


1.4.1 (2013-03-07)
===================

* Fix some feature selection bugs
* Never exit in activate and deactivate
* Improve help and error messages


1.4.0 (2013-03-05)
==================

* Fixed conda pip NAME==VERSION
* Added conda info --license option
* Add source activate and deactivate commands
* Rename the old activate and deactivate to link and unlink
* Add ability for environments to track "features"
* Add ability to distinguish conda build packages from Anaconda packages by adding a "file_hash" meta-data field in info/index.json
* Add conda.builder.share module


1.3.5 (2013-02-05)
==================

* Fixed detecting untracked files on Windows
* Removed backwards compatibility to conda 1.0 version


1.3.4 (2013-01-28)
==================

* Fixed conda installing itself into environments (issue #10)
* Fixed non-existing channels being silently ignored (issue #12)
* Fixed trailing slash in ~/.condarc file cause crash (issue #13)
* Fixed conda list not working when ~/.condarc is missing (issue #14)
* Fixed conda install not working for Python 2.6 environment (issue #17)
* Added simple first cut implementation of remove command (issue #11)
* Pip, build commands: only package up new untracked files
* Allow a system-wide <sys.prefix>/.condarc (~/.condarc takes precedence)
* Only add pro channel if no condarc file exists (and license is valid)


1.3.3 (2013-01-23)
==================

* Fix conda create not filtering channels correctly
* Remove (hidden) --test and --testgui options


1.3.2 (2013-01-23)
==================

* Fix deactivation of packages with same build number note that conda upgrade did not suffer from this problem, as was using separate logic


1.3.1 (2013-01-22)
==================

* Fix bug in conda update not installing new dependencies


1.3.0 (2013-01-22)
==================

* Added conda package command
* Added conda index command
* Added -c, --canonical option to list and search commands
* Fixed conda --version on Windows
* Add this changelog

1.2.1 (2012-11-21)
==================

* Remove ambiguity from conda update command


1.2.0 (2012-11-20)
==================

* ``conda upgrade`` now updates from AnacondaCE to Anaconda (removed upgrade2pro)
* Add versioneer


1.1.0 (2012-11-13)
==================

* Many new features implemented by Bryan


1.0.0 (2012-09-06)
==================

* Initial release
