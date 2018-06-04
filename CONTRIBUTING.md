# Contributing to Conda

## New Issues

If your issue is a bug report or feature request for:

* **a specific conda package**: please file it at <https://github.com/ContinuumIO/anaconda-issues/issues>
* **anaconda.org**: please file it at <https://github.com/Anaconda-Platform/support/issues>
* **repo.anaconda.com**: please file it at <https://github.com/ContinuumIO/anaconda-issues/issues>
* **commands under `conda build`**: please file it at <https://github.com/conda/conda-build/issues>
* **commands under `conda env`**: please file it here!
* **all other conda commands**: please file it here!


## Development Environment, Bash <!-- TODO: make this so (including the msys2 shell on Windows) -->

To set up an environment to start developing on conda code, we recommend the followings steps

1. Choose where you want the project located

       CONDA_PROJECT_ROOT="$HOME/conda"

2. Clone the project, with `origin` being the main repository. Make sure to click the `Fork`
   button above so you have your own copy of this repo.

       GITHUB_USERNAME=kalefranz
       git clone git@github.com:conda/conda "$CONDA_PROJECT_ROOT"
       cd "$CONDA_PROJECT_ROOT"
       git remote --add $GITHUB_USERNAME git@github.com:$GITHUB_USERNAME/conda

3. Create a local development environment, and activate that environment

       source ./dev/start

   This command will create a project-specific base environment at `./devenv`. If
   the environment already exists, this command will just quickly activate the
   already-created `./devenv` environment.

   To be sure that the conda code being interpreted is the code in the project directory,
   look at the value of `conda location:` in the output of `conda info --all`.

4. Run conda's unit tests using GNU make

       make unit

   or alternately with pytest

       py.test -m "not integration and not installed" conda tests

   or you can use pytest to focus on one specific test

       py.test tests/test_create.py -k create_install_update_remove_smoketest


## Development Environment, Windows cmd.exe shell

In these steps, we assume `git` is installed and available on `PATH`.

1. Choose where you want the project located

       set "CONDA_PROJECT_ROOT=%HOMEPATH%\conda"

2. Clone the project, with `origin` being the main repository. Make sure to click the `Fork`
   button above so you have your own copy of this repo.

       set GITHUB_USERNAME=kalefranz
       git clone git@github.com:conda/conda "%CONDA_PROJECT_ROOT%"
       cd "%CONDA_PROJECT_ROOT%"
       git remote --add %GITHUB_USERNAME% git@github.com:%GITHUB_USERNAME%/conda

   To be sure that the conda code being interpreted is the code in the project directory,
   look at the value of `conda location:` in the output of `conda info --all`.

3. Create a local development environment, and activate that environment

       .\dev\start.bat

   This command will create a project-specific base environment at `.\devenv`. If
   the environment already exists, this command will just quickly activate the
   already-created `.\devenv` environment.


## Conda Contributor License Agreement

In case you're new to CLAs, this is rather standard procedure for larger projects.
[Django](https://www.djangoproject.com/foundation/cla/) and even
[Python](https://www.python.org/psf/contrib/contrib-form/) itself both use something similar.

### Process

New contributors should email kfranz@anaconda.com to request a Contributor License Agreement that
can be electronically signed. A signed contributor license agreement for a pull request author
needs to be on file with Anaconda, Inc. for pull requests to be merged. A record of signatories is
kept in the [`.cla-signers`](https://github.com/conda/conda/blob/master/.cla-signers) file in the
project root.

### Individual Contributor License Agreement – Conda Code Organization

In order to clarify the intellectual property license granted with Contributions from any person 
or entity, all projects under the **Conda Code Organization** (“Conda”) must have a Contributor 
License Agreement (“Agreement”) on file that has been signed by each Contributor, indicating 
agreement to the license terms below for each project. This license is for your protection as a 
Contributor as well as the protection of **Anaconda, Inc.** (“Anaconda”) as project manager and 
Conda users; it does not change your rights to use your own Contributions for any other purpose. 
This agreement applies to any current and all future Conda projects, including conda, conda-build, 
constructor, and associated projects under the Conda Code Organization. While currently hosted on 
GitHub at https://github.com/conda, the project hosting site is subject to change at Anaconda's 
sole discretion. 

You accept and agree to the following terms and conditions for Your present and future 
Contributions submitted to Anaconda under Conda. In return, Anaconda shall not use Your 
Contributions in a way that is contrary to the public benefit. Except for the license granted 
herein to Anaconda and recipients of software distributed by Anaconda, you reserve all right, 
title, and interest in and to Your Contributions.

1. Definitions. "You" (or "Your") shall mean the copyright owner or legal entity authorized 
by the copyright owner that is making this Agreement with Anaconda. For legal entities, the entity 
making a Contribution and all other entities that control, are controlled by, or are under common 
control with that entity are considered to be a single Contributor. For the purposes of this 
definition, "control" means (i) the power, direct or indirect, to cause the direction or 
management of such entity, whether by contract or otherwise, or (ii) ownership of fifty percent 
(50%) or more of the outstanding shares, or (iii) beneficial ownership of such entity. 
"Contribution" shall mean any original work of authorship, including any modifications or 
additions to an existing work, that is intentionally submitted by You to Anaconda for inclusion 
in, or documentation of, any of the projects owned or managed by Anaconda (the "Work"). For the 
purposes of this definition, "submitted" means any form of electronic, verbal, or written 
communication sent to Anaconda or its representatives, including but not limited to communication 
on electronic mailing lists, source code control systems, and issue tracking systems that are 
managed by, or on behalf of, Anaconda for the purpose of discussing and improving the Work, but 
excluding communication that is conspicuously marked or otherwise designated in writing by You as 
"Not a Contribution."

2. Grant of Copyright License. Subject to the terms and conditions of this Agreement, You hereby 
grant to Anaconda and to recipients of software distributed by Anaconda a perpetual, worldwide, 
non-exclusive, no-charge, royalty-free, irrevocable copyright license to reproduce, prepare 
derivative works of, publicly display, publicly perform, sublicense, and distribute Your 
Contributions and such derivative works.

3. Grant of Patent License. Subject to the terms and conditions of this Agreement, You hereby 
grant to Anaconda and to recipients of software distributed by Anaconda a perpetual, worldwide, 
non-exclusive, no-charge, royalty-free, irrevocable (except as stated in this section) patent 
license to make, have made, use, offer to sell, sell, import, and otherwise transfer the Work, 
where such license applies only to those patent claims licensable by You that are necessarily 
infringed by Your Contribution(s) alone or by combination of Your Contribution(s) with the Work 
to which such Contribution(s) was submitted. If any entity institutes patent litigation against 
You or any other entity (including a cross-claim or counterclaim in a lawsuit) alleging that Your
Contribution, or the Work to which You have contributed, constitutes direct or contributory patent
infringement, then any patent licenses granted to that entity under this Agreement for that
Contribution or Work shall terminate as of the date such litigation is filed.

4. You represent that you are legally entitled to grant the above license. If your employer(s) has
rights to intellectual property that you create that includes your Contributions, You represent
that you have received permission to make Contributions on behalf of that employer, that your
employer has waived such rights for your Contributions to Anaconda, or that your employer has
executed a separate Corporate Contributor License Agreement with Anaconda. 

5. You represent that each of Your Contributions is Your original creation (see Section 7 for
submissions on behalf of others). You represent that Your Contribution submissions include
complete details of any third-party license or other restriction (including, but not limited to,
related patents and trademarks) of which you are personally aware and which are associated with
any part of Your Contributions. 

6.	You are not expected to provide support for Your Contributions, except to the extent You
desire to provide support. You may provide support for free, for a fee, or not at all. Unless
required by applicable law or agreed to in writing, You provide Your Contributions on an "AS IS"
BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied, including, without
limitation, any warranties or conditions of TITLE, NONINFRINGEMENT, MERCHANTABILITY, or FITNESS
FOR A PARTICULAR PURPOSE. 

7. Should You wish to submit work that is not Your original creation, You may submit it to
Anaconda separately from any Contribution, identifying the complete details of its source and of
any license or other restriction (including, but not limited to, related patents, trademarks,
and license agreements) of which you are personally aware, and conspicuously marking the work as
"Submitted on behalf of a third-party: [named here]".

8. You agree to notify Anaconda of any facts or circumstances of which you become aware that
would make these representations inaccurate in any respect.
