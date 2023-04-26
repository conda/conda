<!-- These docs are updated and synced from https://github.com/conda/infra -->

## Release Process

> **Note:**
> Throughout this document are references to the version number as `YY.M.0`, this should be replaced with the correct version number. Do **not** prefix the version with a lowercase `v`.

[epic template]: ../../issues/new?assignees=&labels=epic&template=epic.yml
[rever docs]: https://regro.github.io/rever-docs
[compare]: ../../compare
[new release]: ../../releases/new
[release docs]: https://docs.github.com/en/repositories/releasing-projects-on-github/automatically-generated-release-notes

### 1. Open the Release Issue.

> **Note:**
> The [epic template][epic template] is perfect for this, just remember to remove the https://github.com/conda/infra/labels/epic label.

<details>
<summary><code>GitHub Issue Template</code></summary>

```markdown
### Summary

Placeholder for `conda YY.M.0` release.

### Tasks

[milestone]: https://github.com/conda/conda/milestone/56
[releases]: https://github.com/conda/conda/releases
[main]: https://github.com/AnacondaRecipes/conda-feedstock
[conda-forge]: https://github.com/conda-forge/conda-feedstock

- [ ] [Complete outstanding PRs][milestone]
- [ ] Create release PR
    - See release process https://github.com/conda/infra/issues/541
- [ ] [Publish Release][releases]
- [ ] Create/update `YY.M.x` branch
- [ ] Feedstocks
    - [ ] Bump version [Anaconda's main][main]
    - [ ] Bump version [conda-forge][conda-forge]
    - Link any other feedstock PRs that are necessary
- [ ] Hand off to the Anaconda packaging team
- [ ] Announce release
    - [ ] Slack
    - [ ] Twitter
```

</details>


### 2. Ensure `rever.xsh` and `news/TEMPLATE` are up to date.

These are synced from https://github.com/conda/infra.

<details>
<summary><h3>3. Run Rever.</h3></summary>

Currently, there are only 2 activities we use rever for, (1) aggregating the authors and (2) updating the changelog. Aggregating the authors can be an error-prone process and also suffers from builtin race conditions (i.e. to generate an updated `.authors.yml` we need an updated `.mailmap` but to have an updated `.mailmap` we need an updated `.authors.yml`). This is why the following steps are very heavy-handed (and potentially repetitive) in running rever commands, undoing commits, squashing/reordering commits, etc.

1. Install [`rever`][rever docs] and activate the environment:

    ```bash
    $ conda create -n rever conda-forge::rever
    $ conda activate rever
    (rever) $
    ```

2. Clone and `cd` into the repository if you haven't done so already:

    ```bash
    (rever) $ git clone git@github.com:conda/conda.git
    (rever) $ cd conda
    ```

2. Create a release branch:

    ```bash
    (rever) $ git checkout -b release-YY.M.0
    ```

2. Run `rever --activities authors`:

    > **Note:**
    > Include `--force` when re-running any rever commands for the same `<VERSION>`, otherwise, rever will skip the activity and no changes will be made (i.e., rever remembers if an activity has been run for a given version).

    ```bash
    (rever) $ rever --activities authors --force <VERSION>
    ```

    - If rever finds that any of the authors are not correctly represented in `.authors.yml` it will produce an error. If the author that the error pertains to is:
        - **a new contributor**: the snippet suggested by rever should be added to the `.authors.yml` file.
        - **an existing contributor**, a result of using a new name/email combo: find the existing author in `.authors.yml` and add the new name/email combo to that author's `aliases` and `alterative_emails`.

    - Once you have successfully run `rever --activities authors` with no errors, review the commit made by rever. This commit will contain updates to one or more of the author files (`.authors.yml`, `.mailmap`, and `AUTHORS.md`). Due to the race condition between `.authors.yml` and `.mailmap`, we want to extract changes made to any of the following keys in `.authors.yml` and commit them separately from the other changes in the rever commit:
        -  `name`
        -  `email`
        -  `github`
        -  `aliases`
        -  `alternate_emails`

      Other keys (e.g., `num_commits` and `first_commit`) do not need to be included in this separate commit as they will be overwritten by rever.

    - Here's a sample run where we undo the commit made by rever in order to commit the changes to `.authors.yml` separately:

        ```bash
        (rever) $ rever --activities authors --force YY.M.0

        # changes were made to .authors.yml as per the prior bullet
        (rever) $ git diff --name-only HEAD HEAD~1
        .authors.yml
        .mailmap
        AUTHORS.md

        # undo commit
        (rever) $ git reset --soft HEAD~1

        # undo changes made to everything except .authors.yml
        (rever) $ git restore --staged --worktree .mailmap AUTHORS.md
        ```

    - Commit these changes to `.authors.yml`:

        ```bash
        (rever) $ git add .
        (rever) $ git commit -m "Updated .authors.yml"
        ```

    - Rerun `rever --activities authors` and finally check that your `.mailmap` is correct by running:

        ```bash
        git shortlog -se
        ```

      Compare this list with `AUTHORS.md`. If they have any discrepancies, additional modifications to `.authors.yml` is needed, so repeat the above steps as needed.

    - Once you are pleased with how the author's file looks, we want to undo the rever commit and commit the `.mailmap` changes separately:

        ```bash
        # undo commit (but preserve changes)
        (rever) $ git reset --soft HEAD~1

        # undo changes made to everything except .mailmap
        (rever) $ git restore --staged --worktree .authors.yml AUTHORS.md
        ```

    - Commit these changes to `.mailmap`:

        ```bash
        (rever) $ git add .
        (rever) $ git commit -m "Updated .mailmap"
        ```

    - Continue repeating the above processes until the `.authors.yml` and `.mailmap` are corrected to your liking. After completing this, you will have at most two commits on your release branch:

        ```bash
        (rever) $ git cherry -v main
        + 86957814cf235879498ed7806029b8ff5f400034 Updated .authors.yml
        + 3ec7491f2f58494a62f1491987d66f499f8113ad Updated .mailmap
        ```


4. Review news snippets (ensure they are all using the correct Markdown format, **not** reStructuredText) and add additional snippets for undocumented PRs/changes as necessary.

    > **Note:**
    > We've found it useful to name news snippets with the following format: `<PR #>-<DESCRIPTIVE SLUG>`.
    >
    > We've also found that we like to include the PR #s inline with the text itself, e.g.:
    >
    > ```markdown
    > ### Enhancements
    >
    > * Add `win-arm64` as a known platform (subdir). (#11778)
    > ```

    - You can utilize [GitHub's compare view][compare] to review what changes are to be included in this release.

    - Add a new news snippet for any PRs of importance that are missing.

    - Commit these changes to news snippets:

        ```bash
        (rever) $ git add .
        (rever) $ git commit -m "Updated news"
        ```

    - After completing this, you will have at most three commits on your release branch:

        ```bash
        (rever) $ git cherry -v main
        + 86957814cf235879498ed7806029b8ff5f400034 Updated .authors.yml
        + 3ec7491f2f58494a62f1491987d66f499f8113ad Updated .mailmap
        + 432a9e1b41a3dec8f95a7556632f9a93fdf029fd Updated news
        ```

5. Run `rever --activities changelog`:

    > **Note:**
    > This has previously been a notoriously fickle step (likely due to incorrect regex patterns in the `rever.xsh` config file and missing `github` keys in `.authors.yml`) so beware of potential hiccups. If this fails, it's highly likely to be an innocent issue.

    ```bash
    (rever) $ rever --activities changelog --force <VERSION>
    ```

    - Any necessary modifications to `.authors.yml`, `.mailmap`, or the news snippets themselves should be amended to the previous commits.

    - Once you have successfully run `rever --activities changelog` with no errors simply revert the last commit (see the next step for why):

        ```bash
        # undo commit (and discard changes)
        (rever) $ git reset --hard HEAD~1
        ```

    - After completing this, you will have at most three commits on your release branch:

        ```bash
        (rever) $ git cherry -v main
        + 86957814cf235879498ed7806029b8ff5f400034 Updated .authors.yml
        + 3ec7491f2f58494a62f1491987d66f499f8113ad Updated .mailmap
        + 432a9e1b41a3dec8f95a7556632f9a93fdf029fd Updated news
        ```

6. Now that we have successfully run the activities separately, we wish to run both together. This will ensure that the contributor list, a side-effect of the authors activity, is included in the changelog activity.

    ```bash
    (rever) $ rever --force <VERSION>
    ```

    - After completing this, you will have at most five commits on your release branch:

        ```bash
        (rever) $ git cherry -v main
        + 86957814cf235879498ed7806029b8ff5f400034 Updated .authors.yml
        + 3ec7491f2f58494a62f1491987d66f499f8113ad Updated .mailmap
        + 432a9e1b41a3dec8f95a7556632f9a93fdf029fd Updated news
        + a5c0db938893d2c12cab12a1f7eb3e646ed80373 Updated authorship for YY.M.0
        + 5e95169d0df4bcdc2da9a6ba4a2561d90e49f75d Updated CHANGELOG for YY.M.0
        ```

7. Since rever does not include stats on first-time contributors, we will need to add this manually.

    - Use [GitHub's auto-generated release notes][new release] to get a list of all new contributors (and their first PR) and manually merge this list with the contributor list in `CHANGELOG.md`. See [GitHub docs][release docs] for how to auto-generate the release notes.

    - Commit these final changes:

        ```bash
        (rever) $ git add .
        (rever) $ git commit -m "Added first contributions"
        ```

    - After completing this, you will have at most six commits on your release branch:

        ```bash
        (rever) $ git cherry -v main
        + 86957814cf235879498ed7806029b8ff5f400034 Updated .authors.yml
        + 3ec7491f2f58494a62f1491987d66f499f8113ad Updated .mailmap
        + 432a9e1b41a3dec8f95a7556632f9a93fdf029fd Updated news
        + a5c0db938893d2c12cab12a1f7eb3e646ed80373 Updated authorship for YY.M.0
        + 5e95169d0df4bcdc2da9a6ba4a2561d90e49f75d Updated CHANGELOG for YY.M.0
        + 93fdf029fd4cf235872c12cab12a1f7e8f95a755 Added first contributions
        ```

8. Push this release branch:

    ```bash
    (rever) $ git push -u upstream release-YY.M.0
    ```

9. Open the Release PR.

    <details>
    <summary>GitHub PR Template</summary>

    ```markdown
    ### Description

    ✂️ snip snip ✂️ the making of a new release.

    Xref #<RELEASE ISSUE>
    ```

    </details>

10. Update Release Issue to include a link to the Release PR.

11. [Create][new release] the release and **SAVE AS A DRAFT** with the following values:

    > **Note:**
    > Only publish the release after the Release PR is merged, until then always **save as draft**.

    | Field | Value |
    |---|---|
    | Choose a tag | `YY.M.0` |
    | Target | `main` |
    | Body | copy/paste blurb from `CHANGELOG.md` |

</details>

### 4. Wait for review and approval of Release PR.

### 5. Merge Release PR and Publish Release.

### 6. Create a new branch (`YY.M.x`) corresponding with the release.

### 7. Open PRs to bump main and conda-forge feedstocks to use `YY.M.0`.

### 8. Hand off to Anaconda's packaging team.

<details>
<summary>Internal process</summary>

1. Open packaging request in #package_requests, include links to the Release PR and feedstock PRs.

2. Message packaging team/PM to let them know that a release has occurred and that you are the release manager.

</details>

### 9. Continue championing and shepherding.

Remember to continue updating the Release Issue with the latest details as tasks are completed.
