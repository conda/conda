# Contributing to conda

Thank you for your interest in improving conda! Below, we describe how our
development process works and how you can be a part of it.

*Already know how to contribute and need help setting up your development environment?
[Read the development environment guide here][development-environment]*

## Hosted on GitHub

All development currently takes place on [GitHub][github]. This means we make extensive
use of the project management tools they provide such as [issues](https://github.com/conda/conda/issues)
and [projects](https://github.com/orgs/conda/projects).

## Code of Conduct

When you decide to contribute to this project, it is important to adhere to our
code of conduct, which is currently the [NumFOCUS Code of Conduct](https://www.numfocus.org/code-of-conduct).
Please read it carefully.

## Conda Contributor License Agreement

To begin contributing to this repository, you need to sign the Conda
Contributor License Agreement (CLA). In case you're new to CLAs, this
is a rather standard procedure for larger projects.
[Django](https://www.djangoproject.com/foundation/cla/) and
[Python](https://www.python.org/psf/contrib/contrib-form/) for example
both use similar agreements.

[Click here to sign the Conda Contributor License Agreement][conda cla].

A record of prior signatories is kept in a [separate repo in conda's GitHub][clabot] organization.

## Ways to contribute

Below are all the ways you can get involved in with conda.

### Bug reports and feature requests

Bug reports and feature requests are always welcome. To file a new issue,
[head to the issue form](https://github.com/conda/conda/issues/new/choose).

It should be noted that `conda-build` issues need to be filed separately at
[its issue tracker](https://github.com/conda/conda-build/issues).

For all other types of issues, please head to [Anaconda.org's "Report a Bug" page][anaconda-bug-report].
For even more information and documentation on everything related to Anaconda, head to the
[Support Center at Anaconda Nucleus][anaconda-support].

Before submitting an issue via any of these channels, make sure to document it
as well as possible and follow the submission guidelines (this makes everyone's job a lot easier!).

### Contributing your changes to conda

Here are the high level steps you need to take to contribute to conda:

1. [Signup for a GitHub account][github signup] (if you haven't already) and
   [install Git on your system][install git].
2. Sign the [Conda Contributor License Agreement][conda cla].
3. Fork the conda repository to your personal GitHub account by clicking the
   "Fork" button on [https://github.com/conda/conda](https://github.com/conda/conda) and follow GitHub's
   instructions.
4. Work on your proposed solution. [Visit this page if you need help getting your development environment setup][development-environment]
5. When you are ready to submit a change, create a new pull request so that we can merge your changes to our repository.

#### Feature development

For new features, begin by creating documentation for the new feature within
the project so that you can get early input on the design. Documentation
includes design mockups, API reference docs, recording the planned approach in
the feature issue, and creating CLI argument demos without the functionality of
the feature.

#### Change process

In order to maintain proper tracking and visibility, make sure that there are
issues for adding features, fixing bugs, and major refactoring work. For larger
features, break down the work into smaller, manageable issues that are added
to the backlog. When creating a new issue, make sure to use the issue template.

When making a change, try to scope changes to what can be accomplished in less
than a day of work with minimal code changes to facilitate rapid code
reviews—typically fewer than 200
lines of code.

For each change, create a new local branch. However, as long as a
feature remains on the roadmap or backlog, do not create long-lived feature
branches that span multiple pull requests. Instead, you should integrate small
slices of an overall feature directly into the main branch to avoid complex
integration challenges.

#### Continuous code improvement

When making changes, try to follow the Campsite Rule to leave things better
than when you found them. You should enhance the code you encounter, even if
the primary goal is unrelated. This could involve refactoring small sections,
improving readability, or fixing minor bugs. The rule is not about massive
overhauls but about consistently making small, positive changes.

#### Pull Requests

##### Pre-submission Steps

1. Install and run pre-commit hooks
2. Make sure all tests are passing
3. Rebase changes on main if other changes were merged during development
4. Use the Pull Request template if one exists for the project
5. Self-review your code with fresh eyes before requesting external review
6. Draft pull requests are acceptable for early feedback

The Pull Request title should clearly explain the contents of the change. Like
the first line of a commit message, it should be a maximum of 50 characters,
written in an imperative mood, and have no ending period. It should stay
updated if the Pull Request is further refined so that if the Pull Request is
squashed and merged, the commit message reflects what was delivered.

##### Review Requirements

###### Standard Review
Most code changes require one reviewer from the
conda-maintainers team. Directly request a review from the person you
previously identified. If you paired with them during development, continuous
review counts as this requirement.

###### Second Review
Required only when the code author or the first reviewer feels
like it is necessary to get another set of eyes on a proposed change. In this
case, they add someone specific through GitHub’s Request Review feature.
Normally they should also put a comment to the person on what they want the
person to look for.

#### Code review process

The primary goal of code review is ensuring future maintainability of
integrated code. Reviews should not focus on:
- Code formatting (handled by pre-commit hooks)
- Spelling (handled by automated checks)
- Personal coding style preferences
- Test coverage and performance (measured by CI)

If you are conducting a review, adhere to these best practices:
- Provide comprehensive feedback in the first review to minimize review rounds
- Follow-up reviews should focus on whether requested changes resolve original
  comments
- Code should be production-ready and maintainable when merged, but doesn't
  need to be perfect
- If providing feedback outside the core review focus (nitpicks, tips,
  suggestions), clearly mark these as non-blocking comments that don't need to
  be addressed before merging.

##### Review Comments

If you are providing feedback outside the core review focus (nitpicks, tips,
suggestions), clearly mark these as non-blocking comments that don't need to be
addressed before merging.

##### Merging Code

If you are the approving reviewer (typically the first reviewer, or the second
reviewer when needed) and you have completed your review and approved the
changes, you should merge the code immediately to maintain development
velocity.

Normally, we use squash and merge to keep a clean git history. If you are
merging a Pull Request, help ensure that the Pull Request title is updated.
Also you should update the description to remove the list of commit messages
and instead add a detailed explanation of the "what" and "why" of changes.

### Issue sorting

Issue sorting is how we filter incoming issues and get them ready for active development.
To see how this process works for this project, read "[The Issue Sorting Process at conda][sorting]".

*The project maintainers are currently not seeking help with issue sorting, but this may change in the future*


[conda cla]: https://conda.io/en/latest/contributing.html#conda-contributor-license-agreement
[clabot]: https://github.com/conda/infra/blob/main/.clabot
[install git]: https://git-scm.com/book/en/v2/Getting-Started-Installing-Git
[github signup]: https://github.com/signup
[github]: https://github.com/
[anaconda-issues]: https://github.com/ContinuumIO/anaconda-issues/issues
[anaconda-support]: https://anaconda.cloud/support-center
[anaconda-bug-report]: https://anaconda.org/contact/report
[sorting]: https://github.com/conda/infra/blob/main/HOW_WE_USE_GITHUB.md
[development-environment]: https://docs.conda.io/projects/conda/en/latest/dev-guide/development-environment.html

## Conda capitalization standards

1. Conda should be written in lowercase, whether in reference to the tool, ecosystem, packages, or organization.
2. References to the conda command should use code formatting (i.e. `conda`).
3. If the use of conda is not a command and if conda is at the beginning of a sentence, conda should be uppercase.

### Examples

#### In sentences

Beginning a sentence:

- Conda is an open-source package and environment management system.
- `conda install` can be used to install packages.

Conda in the middle of a sentence:

- If a newer version of conda is available, you can use `conda update conda` to update to that version.
- You can find conda packages within conda channels. The `conda` command can search these channels.

#### In titles and headers

Titles and headers should use the same capitalization and formatting standards as sentences.

#### In links

Links should use the same capitalization conventions as sentences. Because the conda docs currently use reStructuredText (RST) as a markup language, and [RST does not support nested inline markup](https://docutils.sourceforge.io/FAQ.html#is-nested-inline-markup-possible), documentation writers should avoid using code backtick formatting inside links.
