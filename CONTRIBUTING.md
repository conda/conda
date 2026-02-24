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

## Generative AI

You're welcome to use generative AI tools when contributing to conda. However, please keep the following in mind:

- You are responsible for all of your contributions. Review and understand any AI-generated content before including it in a Pull Request.
- You have read and understood the [conda license](https://github.com/conda/conda/blob/main/LICENSE) and [conda contributor license agreement](https://docs.conda.io/en/latest/contributing.html#conda-contributor-license-agreement), especially in terms of submitting your contribution as an original work of authorship.
- Be prepared to engage during contribution review. Reviewers expect to discuss the changes with you directly. Do not copy and paste AI responses.
- Make minimal, focused changes. AI tools sometimes rewrite more than necessary, making reviews harder. Prefer small, targeted edits that match the existing style and patterns.
- Don't bypass tests. Ensure AI-assisted changes actually fix the underlying problem rather than altering tests to make them pass.
- Do not use AI agents or similar automated systems to submit your contributions or review Pull Requests autonomously.

Pull Requests consisting of unchecked AI-generated content may be closed. Maintainer time is limited and contributions should be high quality, regardless of the tools used to create them.

The [Conda Code of Conduct](https://github.com/conda/conda/blob/main/CODE_OF_CONDUCT.md) applies.

## Paid Contribution Schemes

While we support open source contributors receiving financial compensation, we do not accept contributions motivated by cryptocurrency payments, bounties, or similar gamification schemes. These systems incentivize low-quality, high-volume contributions that waste limited maintainer time.

If you would like to add conda to such a system, or believe your situation warrants an exception, please reach out ahead of time on [Zulip](https://conda.zulipchat.com).

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

Here are steps you need to take to contribute to conda:

1. [Signup for a GitHub account][github signup] (if you haven't already) and
   [install Git on your system][install git].
2. Sign the [Conda Contributor License Agreement][conda cla].
3. Fork the conda repository to your personal GitHub account by clicking the
   "Fork" button on [https://github.com/conda/conda](https://github.com/conda/conda) and follow GitHub's
   instructions.
4. Work on your proposed solution. [Visit this page if you need help getting your development environment setup][development-environment]
5. When you are ready to submit a change, create a pull request.

#### Your first contribution

For your first contribution, we recommend:

- Look for issues labeled with `good first issue`
- Start with small changes like documentation or minor bug fixes
- Read through existing code to understand the project structure and our
  patterns
- Asking questions if you need help, see the [getting help](#getting-help)
  section below.

#### Change process

In order to maintain proper tracking and visibility, make sure that there are
issues for adding features, fixing bugs, and major refactoring work. When
creating a new issue, make sure to use the issue template.

When making a change, try to scope changes to what can be accomplished in less
than a day of work with minimal code changes to facilitate rapid code
reviews—typically fewer than 200 lines of code.

Create a new local branch for each change. Keep your changes focused on a
single issue to make reviews easier.

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
written in an imperative mood, and have no ending period.

##### Review requirements

Most code changes require one reviewer from the conda-maintainers team. When
you submit a Pull Request, that group will automatically be assigned as the
reviewer.

##### What to expect during code review

The primary goal of code review is to ensure maintainability of
integrated code. Reviews will focus on:

- Code correctness and logic
- Maintainability and readability
- Consistency with project patterns and practices

Reviews will NOT focus on:
- Code formatting (handled by pre-commit hooks)
- Minor style preferences
- Test coverage and performance (measured by CI)

If you receive feedback, don't worry! Code review is a collaborative process
to make the code as good as possible. Address the feedback and feel free to
ask questions if anything is unclear.

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

## Getting help

If you need help with your contribution:

- Comment on the issue you're working on
- Join our [community chat channels](https://conda.zulipchat.com)

We're here to help and appreciate your contribution!
