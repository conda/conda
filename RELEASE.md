<!-- edit this in https://github.com/conda/infrastructure -->

[epic template]: https://github.com/conda/conda/issues/new?assignees=&labels=epic&template=epic.yml
[compare]: https://github.com/conda/conda/compare
[new release]: https://github.com/conda/conda/releases/new
[infrastructure]: https://github.com/conda/infrastructure
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

#### Title:
```markdown
Release `YY.MM.x`
```

#### Body:
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
[zulip]: https://conda.zulipchat.com/#narrow/channel/480811-releases

<details open>  <!-- feel free to remove the open attribute once this section is completed -->
<summary><h4>The week before release week</h4></summary>

- [ ] Create release branch (named `YY.MM.x`)
- [ ] Ensure release candidates are being successfully built (see `conda-canary/label/rc-conda-YY.MM.x`)
- [ ] [Complete outstanding PRs][milestone]
- [ ] Check for deprecated features
- [ ] Test release candidates
    <!-- indicate here who has signed off on testing -->

</details>

<details open>  <!-- feel free to remove the open attribute once this section is completed -->
<summary><h4>Release week</h4></summary>

- [ ] Create release PR (see [release process][process])
- [ ] Create Zulip thread on [#releases][zulip]
    - [ ] Announce `YY.MM.MICRO` in-progress
- [ ] [Publish release][releases]
- [ ] Merge `YY.MM.x` back into `main`
- [ ] Activate the `YY.MM.x` branch on [ReadTheDocs][ReadTheDocs]
- [ ] Bump/update feedstocks
    - [ ] [Anaconda, Inc.'s feedstock][main]
    - [ ] [conda-forge feedstock][conda-forge]
- [ ] Hand off to packaging team(s)
- [ ] Announce release
    - [ ] Create & publish conda.org blog post
    - [ ] Post on Zulip thread

</details>
```
</details>

If a patch release is necessary, reopen the original release issue and append the following template to the release issue summary.

<details>
<summary><h3>Patch Release Template</h3></summary>

#### Append to existing 'Release `YY.MM.x`' issue:
```markdown
<details open>  <!-- feel free to remove the open attribute once this section is completed -->
<summary><h4>Patch YY.MM.MICRO</h4></summary>

- [ ] <!-- list issues & PRs that need to be resolved here -->
- [ ] Create release PR (see [release process][process])
- [ ] Update Zulip thread on [#releases][zulip]
    - [ ] Announce `YY.MM.MICRO` in-progress
- [ ] [Publish release][releases]
- [ ] Merge `YY.MM.x` back into `main`
- [ ] Bump/update feedstocks
    - [ ] [Anaconda, Inc.'s feedstock][main]
    - [ ] [conda-forge feedstock][conda-forge]
- [ ] Hand off to packaging team(s)
- [ ] Announce release
    - [ ] Post on Zulip thread

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

## 4. Ensure `news/TEMPLATE` and release workflows are up to date.

These are synced from [`conda/infrastructure`][infrastructure]. News validation uses `conda/actions/check-news`; release-note generation uses `conda/actions/prepare-release`.

<details>
<summary><h2>5. Prepare release notes. (ideally done on the Monday of release week)</h2></summary>

The release notes flow is split into two pieces:

- Contributor and mailmap maintenance remains separate from news generation.
- News snippets are aggregated by the `Prepare release notes` workflow after `Tests` succeeds on the release branch.

1. Review news snippets and add any missing user-facing entries before the release branch test run finishes.

    > **Note:** <!-- GH doesn't support nested admonitions, see https://github.com/orgs/community/discussions/16925 -->
    > Name news snippets with the following format: `<PR #>-<DESCRIPTIVE SLUG>`.
    >
    > Include the PR number inline with the text itself, e.g.:
    >
    > ```markdown
    > ### Enhancements
    >
    > * Add `win-arm64` as a known platform (subdir). (#11778)
    > ```

    - Use [GitHub's compare view][compare] to review what changes are included in this release. Compare the current release branch against the previous release branch.

    - Add a new news snippet for any important PRs that are missing one.

2. Wait for `Tests` to pass on the `YY.MM.x` release branch.

    The `Prepare release notes` workflow runs from that successful `workflow_run`, validates that it came from a trusted push to this repository, and opens or updates a `release-notes-YY.MM.MICRO` PR targeting `YY.MM.x`.

3. Review the generated release-notes PR.

    - The PR should modify only `CHANGELOG.md` and consumed `news/` snippets.
    - The PR body should describe the generated release-notes update.
    - The changelog should preserve the news text under `Enhancements`, `Bug fixes`, `Deprecations`, `Docs`, and `Other`.
    - The consumed `news/` snippets should be deleted from the generated branch.

4. If the changelog needs wording changes, edit the generated release-notes PR branch and rerun checks.

5. Update the release issue to include a link to the release-notes PR.

6. [Create][new release] the release and **SAVE AS A DRAFT** with the following values:

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
