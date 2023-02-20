<!-- absolute URLs -->
[conda-org]: https://github.com/conda
[sub-team]: https://github.com/conda-incubator/governance#sub-teams

[project-planning]: https://github.com/orgs/conda/projects/2/views/11
[project-sorting]: https://github.com/orgs/conda/projects/2/views/11
[project-support]: https://github.com/orgs/conda/projects/2/views/12
[project-backlog]: https://github.com/orgs/conda/projects/2/views/13
[project-sprint]: https://github.com/orgs/conda/projects/2/views/14

[docs-toc]: https://github.blog/changelog/2021-04-13-table-of-contents-support-in-markdown-files/
[docs-actions]: https://docs.github.com/en/actions
[docs-saved-reply]: https://docs.github.com/en/get-started/writing-on-github/working-with-saved-replies/creating-a-saved-reply

[workflow-sync]: https://github.com/conda/infra/blob/main/.github/workflows/sync.yml
[labels-global]: https://github.com/conda/infra/blob/main/.github/global.yml

<!-- relative URLs -->
[workflow-issues]: /.github/workflows/issues.yml
[workflow-project]: /.github/workflows/project.yml
[labels-local]: /.github/labels.yml

## How We Use GitHub

> **Note**
> For easy navigation use [GitHub's table of contents feature][docs-toc].

This document seeks to outline how we as a community use GitHub Issues to track bugs and feature requests while still catering to development practices & project management (*e.g.*, release cycles, feature planning, priority sorting, etc.).

<!-- only include high-level topics or particularly noteworthy sections here -->
Topics:
  - [What is Issue Sorting?](#what-is-issue-sorting)
  - [Types of tickets](#types-of-tickets)
    - [Normal Ticket/Issue](#normal-ticketissue)
    - [Epics](#epics)
    - [Spikes](#spikes)


### What is "Issue Sorting"?

> **Note**
> "Issue sorting" is similar to that of "triaging", but we've chosen to use different terminology because "triaging" is a word related to very weighty topics (*e.g.*, injuries and war) and we would like to be sensitive to those connotations. Additionally, we are taking a more "fuzzy" approach to sorting (*e.g.*, severities may not be assigned, etc.).

"Issue Sorting" refers to the process of assessing the priority of incoming issues. Below is a high-level diagram of the flow of tickets:

```mermaid
flowchart LR
    subgraph flow_sorting [Issue Sorting]
        board_sorting{{Sorting}}
        board_support{{Support}}

        board_sorting<-->board_support
    end

    subgraph flow_refinement [Refinement]
        board_backlog{{Backlog}}

        board_backlog-- refine -->board_backlog
    end

    subgraph flow_sprint [Sprint]
        board_sprint{{Sprint}}
    end

    state_new(New Issues)
    state_closed(Closed)

    state_new-->board_sorting
    board_sorting-- investigated -->board_backlog
    board_sorting-- duplicates, off-topic -->state_closed
    board_support-- resolved, unresponsive -->state_closed
    board_backlog-- pending work -->board_sprint
    board_backlog-- resolved, irrelevant -->state_closed
    board_sprint-- resolved -->state_closed
```

In order to explain how various `conda` issues are evaluated, the following document will provide information about our sorting process in the form of an FAQ.


#### Why sort issues?

At the most basic "bird's eye view" level, sorted issues will fall into the category of four main priority levels:

- Do now
- Do sometime
- Provide user support
- Never do (_i.e._, close)

At its core, sorting enables new issues to be placed into these four categories, which helps to ensure that they will be processed at a velocity similar to or exceeding the rate at which new issues are coming in. One of the benefits of actively sorting issues is to avoid engineer burnout and to make necessary work sustainable; this is done by eliminating a never-ending backlog that has not been reviewed by any maintainers.

There will always be broad-scope design and architecture implementations that the `conda` maintainers will be interested in pursuing; by actively organizing issues, the sorting engineers will be able to more easily track and tackle both specific and big-picture goals.

#### Who does the sorting?

Sorting engineers are a `conda` governance [sub-team][sub-team]; they are a group of Anaconda and community members who are responsible for making decisions regarding closing issues and setting feature work priorities, amongst other sorting-related tasks.


#### How do items show up for sorting?

New issues that are opened in any of the repositories in the [`conda` GitHub project][conda-org] will show up in the `Sorting` view of the [Planning project][project-planning]. This process is executed via [GitHub Actions][docs-actions]. The two main GitHub Actions workflows utilized for this purpose are [Issues][workflow-issues] and [Project][workflow-project].

The GitHub Actions in the `conda/infra` repository are viewed as canonical; the [Sync workflow][workflow-sync] sends out any modifications to other `conda` repositories from there.


#### What is done about the issues in "sorting" mode?

Issues in the ["Sorting" tab of the project board][project-sorting] have been reviewed by a sorting engineer and are considered ready for the following procedures:

- Mitigation via short-term workarounds and fixes
- Redirection to the correct project
- Determining if support can be provided for errors and questions
- Closing out of any duplicate/off-topic issues

The sorting engineers on rotation are not seeking to _resolve_ issues that arise. Instead, the goal is to understand the ticket and to determine whether it is an issue in the first place, and then to collect as much relevant information as possible so that the maintainers of `conda` can make an informed decision about the appropriate resolution schedule.

Issues will remain in the "Sorting" tab as long as the issue is in an investigatory phase (_e.g._, querying the user for more details, asking the user to attempt other workarounds, other debugging efforts, etc.) and are likely to remain in this state the longest, but should still be progressing over the course of 1-2 weeks.


#### When do items move out of the "Sorting" tab?

The additional tabs in the project board that the issues can be moved to include the following:

- **"Support"** - Any issue in the ["Support" tab of the Planning board][project-support] is a request for support and is not a feature request or a bug report. All issues considered "support" should include the https://github.com/conda/infra/labels/type%3A%3Asupport label.
- **"Backlog"** - The issue has revealed a bug or feature request. We have collected enough details to understand the problem/request and to reproduce it on our own. These issues have been moved into the [Backlog tab of the Planning board][project-backlog] at the end of the sorting rotation during Refinement.
- **"Closed"** - The issue was closed due to being a duplicate, being redirected to a different project, was a user error, a question that has been resolved, etc.


#### Where do items go after being sorted?

All sorted issues will be reviewed by sorting engineers during a weekly Refinement meeting in order to understand how those particular issues fit into the short- and long-term roadmap of `conda`. These meetings enable the sorting engineers to get together to collectively prioritize issues, earmark feature requests for specific future releases (versus a more open-ended backlog), tag issues as ideal for first-time contributors, as well as whether or not to close/reject specific feature requests.

Once issues are deemed ready to be worked on, they will be moved to the [`conda` Backlog tab of the Planning board][project-backlog] on GitHub. Once actively in progress, the issues will be moved to the [Sprint tab of the Planning board][project-sprint] and then closed out once the work is complete.


#### What is the purpose of having a "Backlog"?

Issues are "backlogged" when they have been sorted but not yet earmarked for an upcoming release. Weekly Refinement meetings are a time when the `conda` engineers will transition issues from "[Sorting][project-sorting]" to "[Backlog][project-backlog]". Additionally, this time of handoff will include discussions around the kind of issues that were raised, which provides an opportunity to identify any patterns that may point to a larger problem.


#### What is the purpose of a "development sprint"?

After issues have been sorted and backlogged, they will eventually be moved into the "Sprint Candidate", "Short-Term", "Medium-Term", "Long-Term", or "No Time Frame" sections of the [Backlog tab of the Planning board][project-backlog] and get one or more sprint cycles dedicated to them.

The purpose of a development sprint is to enable a steady delivery of enhancements, features, and bug fixes by setting aside pre-determined portions of time that are meant for focusing on specifically-assigned items.

Sprints also serve to focus the engineering team's attention on more accurate planning for what is to come during the entire release cycle, as well as keep the scope of development work concise. They enable the setting aside of dedicated time for the engineers to resolve any problems with the work involved, instead of pushing these problems to the end of the release cycle when there may not be any time remaining to fix issues.


#### How does labeling work?

Labeling is a very important means for sorting engineers to keep track of the current state of an issue with regards to the asynchronous nature of communicating with users. Utilizing the proper labels helps to identify the severity of the issue as well as to quickly understand the current state of a discussion.

Generally speaking, labels with the same category are considered mutually exclusive but in some cases labels sharing the same category can occur concurrently as they indicate qualifiers as opposed to types. For example, we may have the following types, https://github.com/conda/infra/labels/type%3A%3Abug, https://github.com/conda/infra/labels/type%3A%3Afeature, and https://github.com/conda/infra/labels/type%3A%3Adocumentation, where for any one issue there would be _at most_ **one** of these to be defined (_i.e._ an issue shouldn’t be a bug _and_ a feature request at the same time). Alternatively, with issues involving specific operating systems (_i.e._, https://github.com/conda/infra/labels/os%3A%3Alinux, https://github.com/conda/infra/labels/os%3A%3Amacos, and https://github.com/conda/infra/labels/os%3A%3Awindows), an issue could be labeled with one or more depending on the system(s) the issue is occurring on.

Please note that there are also automation policies in place. For example, if an issue is labeled as https://github.com/conda/infra/labels/pending%3A%3Afeedback and https://github.com/conda/infra/labels/unreproducible, that issue will be auto-closed after a month of inactivity.


#### How are new labels defined?

Labels are defined using a scoped syntax with an optional high-level category (_e.g._, source, tag, type, etc.) and a specific topic, much like the following:

- `[topic]`
- `[category::topic]`
- `[category::topic-phrase]`

This syntax helps with issue sorting enforcement; at minimum, both `type` and `source` labels should be specified on each issue before moving it from "`Sorting`" to "`Backlog`".

There are a number of labels that have been defined for the different `conda` projects. In order to create a streamlined sorting process, label terminologies are standardized using similar (if not the same) labels.


#### How are new labels added?

New **global** labels (_i.e._, generic labels that apply equally to all `conda` repos) can be added to the `conda/infra`'s [`.github/global.yml` file][labels-global]; new **local** labels (_i.e._, labels specific to particular `conda` repos) can be added to each repository's [`.github/labels.yml`][labels-local] file. All new labels should follow the labeling syntax described in the "How are new labels defined?" section of this document.


#### Are there any templates to use as responses for commonly-seen issues?

Some of the same types of issues appear regularly (_e.g._, issues that are duplicates of others, tickets that should be filed in the Anaconda issue tracker, errors that are due to a user's specific setup/environment, etc.).

Below are some boilerplate responses for the most commonly-seen issues to be sorted:

<details>
<summary><b>Duplicate Issue</b></summary>

<pre>

This is a duplicate of <b>[link to primary issue]</b>; please feel free to continue the discussion there.
</pre>

> **Warning**
> Apply the https://github.com/conda/infra/labels/duplicate label to the issue being closed and https://github.com/conda/infra/labels/duplicate%3A%3Aprimary to the original issue.

</details>

<details>
<summary><b>Requesting an Uninstall/Reinstall of <code>conda</code></b></summary>

<pre>

Please uninstall your current version of `conda` and reinstall the latest version.
Feel free to use either the [miniconda](https://docs.conda.io/en/latest/miniconda.html)
or [anaconda](https://www.anaconda.com/products/individual) installer,
whichever is more appropriate for your needs.
</pre>

</details>

<details>
<summary><b>Redirect to Anaconda Issue Tracker</b></summary>

<pre>

Thank you for filing this issue! Unfortunately, this is off-topic for this repo.
If you are still encountering this issue please reopen in the
[Anaconda issue tracker](https://github.com/ContinuumIO/anaconda-issues/issues)
where `conda` installer/package issues are addressed.
</pre>

> **Warning**
> Apply the https://github.com/conda/infra/labels/off-topic label to these tickets before closing them out.

</details>

<details>
<summary><b>Redirecting to Nucleus Forums</b></summary>

<pre>

Unfortunately, this issue is outside the scope of support we offer via GitHub;
if you continue to experience the problems described here,
please post details to the [Nucleus forums](https://community.anaconda.cloud/).
</pre>

> **Warning**
> Apply the https://github.com/conda/infra/labels/off-topic label to these tickets before closing them out.

</details>

In order to not have to manually type or copy/paste the above repeatedly, please note that it's possible to add text for the most commonly-used responses via [GitHub's "Add Saved Reply" option][docs-saved-reply].


### Types of Tickets

#### Standard Ticket/Issue

TODO

#### Epics

TODO

#### Spikes

TODO
