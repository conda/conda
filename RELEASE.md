<!-- edit this in https://github.com/conda/infrastructure -->

[epic template]: https://github.com/conda/conda/issues/new?assignees=&labels=epic&template=epic.yml
[compare]: https://github.com/conda/conda/compare
[new release]: https://github.com/conda/conda/releases/new
[infrastructure]: https://github.com/conda/infrastructure
[rever docs]: https://regro.github.io/rever-docs
[release docs]: https://docs.github.com/en/repositories/releasing-projects-on-github/automatically-generated-release-notes
[merge conflicts]: https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/addressing-merge-conflicts/about-merge-conflicts
[Anaconda Recipes]: https://github.com/AnacondaRecipes/conda-feedstock
[conda-forge]: https://github.com/conda-forge/conda-feedstock

# Release Process

> [!NOTE]
> Throughout this document are references to the version number as `YY.MM.MICRO`, this should be replaced with the correct version number. Do **not** prefix the version with a lowercase `v`.

## 1. Open the release issue and cut a release branch. (do this ~1 week prior to release)

> [!NOTE]
> The new release branch should adhere to the naming convention of `YY.MM.x` (note the difference to `YY.MM.MICRO`). In the case of patch/hotfix releases, however, do NOT cut a new release branch; instead, use the previously-cut `YY.MM.x` release branch.

Use the issue template below to create the release issue. After creating the release issue, pin it for easy access.

<details>
<summary><h3>Release Template</h3></summary>

```markdown
### Summary

Placeholder for `conda YY.MM.x` release.

| Pilot | <pilot> |
|---|---|
| Co-pilot | <copilot> |

### Tasks

[milestone]: https://github.com/conda/conda/milestone/<milestone>
[process]: https://github.com/conda/conda/blob/main/RELEASE.md
[releases]: https://github.com/conda/conda/releases
[main]: https://github.com/AnacondaRecipes/conda-feedstock
[conda-forge]: https://github.com/conda-forge/conda-feedstock
[ReadTheDocs]: https://readthedocs.com/projects/continuumio-conda/

<details open>  <!-- feel free to remove the open attribute once this section is completed -->
<summary><h4>The week before release week</h4></summary>

- [ ] Create release branch (named `YY.MM.x`)
- [ ] Ensure release candidates are being successfully built (see `conda-canary/label/rc-conda-YY.MM.x`)
- [ ] [Complete outstanding PRs][milestone]
- [ ] Test release candidates
    <!-- indicate here who has signed off on testing -->

</details>

<details open>  <!-- feel free to remove the open attribute once this section is completed -->
<summary><h4>Release week</h4></summary>

- [ ] Create release PR (see [release process][process])
- [ ] [Publish release][releases]
- [ ] Merge `YY.MM.x` back into `main`
- [ ] Activate the `YY.MM.x` branch on [ReadTheDocs][ReadTheDocs]
- [ ] Feedstocks
    - [ ] Bump version & update dependencies/tests in [Anaconda, Inc.'s feedstock][main]
    - [ ] Bump version & update dependencies/tests in [conda-forge feedstock][conda-forge]
    <!-- link any other feedstock PRs here -->
- [ ] Hand off to the Anaconda packaging team
- [ ] Announce release
    - Blog Post (optional)
        - [ ] conda.org (link to pull request)
    - Long form
        - [ ] Create release [announcement draft](https://github.com/conda/communications)
        - [ ] [Discourse](https://conda.discourse.group/)
        - [ ] [Matrix (conda/conda)](https://matrix.to/#/#conda_conda:gitter.im) (this auto posts from Discourse)
    - Summary
        - [ ] [Twitter](https://twitter.com/condaproject)

</details>
```
</details>

If a patch release is necessary, reopen the original release issue and append the following template to the release issue summary.

<details>
<summary><h3>Patch Release Template</h3></summary>

```markdown
<details open>  <!-- feel free to remove the open attribute once this section is completed -->
<summary><h4>Patch YY.MM.MICRO</h4></summary>

- [ ] <!-- list issues & PRs that need to be resolved here -->
- [ ] Create release PR (see [release process][process])
- [ ] [Publish release][releases]
- [ ] Merge `YY.MM.x` back into `main`
- [ ] Feedstocks
    - [ ] Bump version & update dependencies/tests in [Anaconda, Inc.'s feedstock][main]
    - [ ] Bump version & update dependencies/tests in [conda-forge feedstock][conda-forge]
- [ ] Hand off to the Anaconda packaging team

</details>
```

</details>

> [!NOTE]
> The [epic template][epic template] is perfect for this; remember to remove the **`epic`** label.

> [!NOTE]
> A patch release is like a regular, i.e., follow the same steps in the process as you would for a regular release. Most patches are authored by existing contributors (most likely maintainers themselves) so running `rever <VERSION>` may succeed on the first pass.

## 2. Alert various parties of the upcoming release. (do this ~1 week prior to release)

Let various interested parties know about the upcoming release; at minimum, conda-forge maintainers should be informed. For major features, a blog post describing the new features should be prepared and posted once the release is completed (see the announcements section of the release issue).

## 3. Manually test canary build(s).

### Canary Builds for Manual Testing

Once the release PRs are filed, successful canary builds will be available on `https://anaconda.org/conda-canary/conda/files?channel=rc-conda-YY.MM.x` for manual testing.

> [!NOTE]
> You do not need to apply the `build::review` label for release PRs; every commit to the release branch builds and uploads canary builds to the respective `rc-` label.

## 4. Ensure `rever.xsh` and `news/TEMPLATE` are up to date.

These are synced from [`conda/infrastructure`][infrastructure].

<details>
<summary><h2>5. Run rever. (ideally done on the Monday of release week)</h2></summary>

Currently, there are only 2 activities we use rever for, (1) aggregating the authors and (2) updating the changelog. Aggregating the authors can be an error-prone process and also suffers from builtin race conditions (_i.e._, to generate an updated `.authors.yml` we need an updated `.mailmap` but to have an updated `.mailmap` we need an updated `.authors.yml`). This is why the following steps are very heavy-handed (and potentially repetitive) in running rever commands, undoing commits, squashing/reordering commits, etc.

1. Install [`rever`][rever docs] and activate the environment:

    ```bash
    $ conda create -n rever conda-forge::rever
    $ conda activate rever
    (rever) $
    ```

2. Clone and `cd` into the repository if you haven't done so already:

    ```bash
    (rever) $ git clone git@github.com:/conda.git
    (rever) $ cd conda
    ```

2. Fetch the latest changes from the remote and checkout the release branch created a week ago:

    ```bash
    (rever) $ git fetch upstream
    (rever) $ git checkout YY.MM.x
    ```

2. Create a versioned branch, this is where rever will make its changes:

    ```bash
    (rever) $ git checkout -b changelog-YY.MM.MICRO
    ```

2. Run `rever --activities authors <VERSION>`:

    > **Note:** <!-- GH doesn't support nested admonitions, see https://github.com/orgs/community/discussions/16925 -->
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
        (rever) $ rever --activities authors --force YY.MM.MICRO

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
        (rever) $ git commit -m "Update .authors.yml"
        ```

    - Rerun `rever --activities authors --force <VERSION>` and finally check that your `.mailmap` is correct by running:

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
        (rever) $ git commit -m "Update .mailmap"
        ```

    - Continue repeating the above processes until the `.authors.yml` and `.mailmap` are corrected to your liking. After completing this, you will have at most two commits on your release branch:

        ```bash
        (rever) $ git cherry -v <release branch>
        + 86957814cf235879498ed7806029b8ff5f400034 Update .authors.yml
        + 3ec7491f2f58494a62f1491987d66f499f8113ad Update .mailmap
        ```


4. Review news snippets (ensure they are all using the correct Markdown format, **not** reStructuredText) and add additional snippets for undocumented PRs/changes as necessary.

    > **Note:** <!-- GH doesn't support nested admonitions, see https://github.com/orgs/community/discussions/16925 -->
    > We've found it useful to name news snippets with the following format: `<PR #>-<DESCRIPTIVE SLUG>`.
    >
    > We've also found that we like to include the PR #s inline with the text itself, e.g.:
    >
    > ```markdown
    > ## Enhancements
    >
    > * Add `win-arm64` as a known platform (subdir). (#11778)
    > ```

    - You can utilize [GitHub's compare view][compare] to review what changes are to be included in this release. Make sure you compare the current release branch against the previous one

    - Add a new news snippet for any PRs of importance that are missing.

    - Commit these changes to news snippets:

        ```bash
        (rever) $ git add .
        (rever) $ git commit -m "Update news"
        ```

    - After completing this, you will have at most three commits on your release branch:

        ```bash
        (rever) $ git cherry -v <release branch>
        + 86957814cf235879498ed7806029b8ff5f400034 Update .authors.yml
        + 3ec7491f2f58494a62f1491987d66f499f8113ad Update .mailmap
        + 432a9e1b41a3dec8f95a7556632f9a93fdf029fd Update news
        ```

5. Run `rever --activities changelog`:

    > **Note:** <!-- GH doesn't support nested admonitions, see https://github.com/orgs/community/discussions/16925 -->
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
        (rever) $ git cherry -v <release branch>
        + 86957814cf235879498ed7806029b8ff5f400034 Update .authors.yml
        + 3ec7491f2f58494a62f1491987d66f499f8113ad Update .mailmap
        + 432a9e1b41a3dec8f95a7556632f9a93fdf029fd Update news
        ```

6. Now that we have successfully run the activities separately, we wish to run both together. This will ensure that the contributor list, a side-effect of the authors activity, is included in the changelog activity.

    ```bash
    (rever) $ rever --force <VERSION>
    ```

    - After completing this, you will have at most five commits on your release branch:

        ```bash
        (rever) $ git cherry -v <release branch>
        + 86957814cf235879498ed7806029b8ff5f400034 Update .authors.yml
        + 3ec7491f2f58494a62f1491987d66f499f8113ad Update .mailmap
        + 432a9e1b41a3dec8f95a7556632f9a93fdf029fd Update news
        + a5c0db938893d2c12cab12a1f7eb3e646ed80373 Update authorship for YY.MM.MICRO
        + 5e95169d0df4bcdc2da9a6ba4a2561d90e49f75d Update CHANGELOG for YY.MM.MICRO
        ```

7. Since rever does not include stats on first-time contributors, we will need to add this manually.

    - Use [GitHub's auto-generated release notes][new release] to get a list of all new contributors (and their first PR) and manually merge this list with the contributor list in `CHANGELOG.md`. See [GitHub docs][release docs] for how to auto-generate the release notes.

    - Commit these final changes:

        ```bash
        (rever) $ git add .
        (rever) $ git commit -m "Add first-time contributions"
        ```

    - After completing this, you will have at most six commits on your release branch:

        ```bash
        (rever) $ git cherry -v <release branch>
        + 86957814cf235879498ed7806029b8ff5f400034 Update .authors.yml
        + 3ec7491f2f58494a62f1491987d66f499f8113ad Update .mailmap
        + 432a9e1b41a3dec8f95a7556632f9a93fdf029fd Update news
        + a5c0db938893d2c12cab12a1f7eb3e646ed80373 Update authorship for YY.MM.MICRO
        + 5e95169d0df4bcdc2da9a6ba4a2561d90e49f75d Update CHANGELOG for YY.MM.MICRO
        + 93fdf029fd4cf235872c12cab12a1f7e8f95a755 Add first-time contributions
        ```

8. Push this versioned branch.

    ```bash
    (rever) $ git push -u upstream changelog-YY.MM.MICRO
    ```

9. Open the Release PR targeting the `YY.MM.x` branch.

    <details>
    <summary>GitHub PR Template</summary>

    ```markdown
    ## Description

    ✂️ snip snip ✂️ the making of a new release.

    Xref #<RELEASE ISSUE>
    ```

    </details>

10. Update release issue to include a link to the release PR.

11. [Create][new release] the release and **SAVE AS A DRAFT** with the following values:

    > **Note:** <!-- GH doesn't support nested admonitions, see https://github.com/orgs/community/discussions/16925 -->
    > Only publish the release after the release PR is merged, until then always **save as draft**.

    | Field | Value |
    |---|---|
    | Choose a tag | `YY.MM.MICRO` |
    | Target | `YY.MM.x` |
    | Body | copy/paste blurb from `CHANGELOG.md` |

</details>

## 6. Wait for review and approval of release PR.

## 7. Merge release PR and publish release.

To publish the release, go to the project's release page (e.g., https://github.com/conda/conda/releases) and add the release notes from `CHANGELOG.md` to the draft release you created earlier. Then publish the release.

> [!NOTE]
> Release notes can be drafted and saved ahead of time.

## 8. Merge/cherry pick the release branch over to the `main` branch.

<details>
<summary>Internal process</summary>

1. From the main "< > Code" page of the repository, select the drop down menu next to the `main` branch button and then select "View all branches" at the very bottom.

2. Find the applicable `YY.MM.x` branch and click the "New pull request" button.

3. "Base" should point to `main` while "Compare" should point to `YY.MM.x`.

4. Ensure that all of the commits being pulled in look accurate, then select "Create pull request".

> [!NOTE]
> Make sure NOT to push the "Update Branch" button. If there are [merge conflicts][merge conflicts], create a temporary "connector branch" dedicated to fixing merge conflicts separately from the `YY.MM.x` and `main` branches.

5. Review and merge the pull request the same as any code change pull request.

> [!NOTE]
> The commits from the release branch need to be retained in order to be able to compare individual commits; in other words, a "merge commit" is required when merging the resulting pull request vs. a "squash merge". Protected branches will require permissions to be temporarily relaxed in order to enable this action.

</details>

## 9. Open PRs to bump [Anaconda Recipes][Anaconda Recipes] and [conda-forge][conda-forge] feedstocks to use `YY.MM.MICRO`.

> [!NOTE]
> Conda-forge's PRs will be auto-created via the `regro-cf-autotick-bot`. Follow the instructions below if any changes need to be made to the recipe that were not automatically added (these instructions are only necessary for anyone who is _not_ a conda-forge feedstock maintainer, since maintainers can push changes directly to the autotick branch):
> - Create a new branch based off of autotick's branch (autotick's branches usually use the `regro-cf-autotick-bot:XX.YY.[$patch_number]_[short hash]` syntax)
> - Add any changes via commits to that new branch
> - Open a new PR and push it against the `main` branch
>
> Make sure to include a comment on the original `autotick-bot` PR that a new pull request has been created, in order to avoid duplicating work!  `regro-cf-autotick-bot` will close the auto-created PR once the new PR is merged.
>
> For more information about this process, please read the ["Pushing to regro-cf-autotick-bot branch" section of the conda-forge documentation](https://conda-forge.org/docs/maintainer/updating_pkgs.html#pushing-to-regro-cf-autotick-bot-branch).


## 10. Hand off to Anaconda's packaging team.

> [!NOTE]
> This step should NOT be done past Thursday morning EST; please start the process on a Monday, Tuesday, or Wednesday instead in order to avoid any potential debugging sessions over evenings or weekends.

<details>
<summary>Internal process</summary>

1. Open packaging request in #package_requests Slack channel, include links to the Release PR and feedstock PRs.

2. Message packaging team/PM to let them know that a release has occurred and that you are the release manager.

</details>

## 11. Continue championing and shepherding.

Remember to make all relevant announcements and continue to update the release issue with the latest details as tasks are completed.
