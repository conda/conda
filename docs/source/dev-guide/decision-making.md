[governance]: https://github.com/conda/governance
[how-we-use-github]: https://github.com/conda/conda/blob/main/HOW_WE_USE_GITHUB.md#code-review-and-merging
[rapid]: https://cio-wiki.org/wiki/RAPID_Approach
[rfc7282]: https://www.rfc-editor.org/rfc/rfc7282

# Decision Making for conda Maintainers

:::{note}
This page is intended for current and prospective members of the
**conda-maintainers** team, not for all contributors.
:::

This page describes how the conda-maintainers team makes decisions on the
repositories they maintain, including conda. For background on conda Organization
governance (Steering Council, project team membership, voting), see the
[conda governance repository][governance].

## Principles

The conda-maintainers uses a lightweight version of the [RAPID framework][rapid] to keep
decisions clear and avoid both bottlenecks and diffusion of accountability. The
core idea is that every significant decision has a named owner, a defined set of
people who must agree before it proceeds, and a defined set of people whose
input is sought but who cannot block it.

Shared codebase ownership means everyone can contribute anywhere. It does not
mean every decision requires consensus from everyone.

## Roles

- **Recommend (R):** Investigates the problem, proposes the solution, and
  drives the plan. For features, this is the feature owner. For smaller changes,
  this is the PR author.
- **Agree (A):** Must approve before the decision is final. For PRs, this is
  the reviewer the PR author identified ahead of time — ideally someone they
  collaborated with during development. Kept deliberately small — additional
  commenters on a PR are giving Input, not Agree.
- **Perform (P):** Executes the decision. Often the whole team or a subset of
  contributors. Shared ownership means most engineers are in this role on most
  features.
- **Input (I):** Consulted but not a blocker. Community contributors, users,
  and other maintainers provide Input via GitHub issues and PR threads.
- **Decide (D):** Single accountable decision-maker for this decision type. For
  in-scope technical decisions on a feature, this is the feature owner. For
  major architectural decisions with ecosystem impact this is the technical lead
  on the conda-maintainers team.

## The Feature Owner Role

For larger features or epics, the conda-maintainers assign a feature owner, a
rotating conda-maintainer who is accountable for the requirements, the plan,
and execution of that feature. The feature owner does not do all the work
themselves.

The feature owner:

- Holds R and D for the duration of the feature
- Opens and drives the GitHub issue discussion to gather community Input before
  work begins
- Makes in-scope technical decisions during execution without requiring
  consensus on every choice

The feature owner role rotates across conda-maintainers to build shared
decision-making experience.

## Decision Tiers

### Tier 1 — PR and story-level decisions

Most changes fall here. The PR author is R, the reviewer they identified ahead
of time is A, and the approving reviewer merges. Community members commenting on
the PR are providing Input.

Directly requesting a review from the person you previously identified to work
with is preferred to optimize teamwork. If you paired with them during
development, continuous review counts as this requirement. See [How We Use
GitHub — Code Review and Merging][how-we-use-github].

### Tier 2 — Feature-level architectural decisions

Changes that affect solver behavior, plugin APIs, [deprecation schedules](deprecations),
cross-platform behavior, or other areas with ecosystem-wide impact. The feature
owner is R, affected community tool authors and maintainers are I, senior
maintainers are A on PRs, and the feature owner is D for implementation
decisions.

## Input vs. Agree

A common failure mode in shared-ownership projects is treating every reviewer
comment as a potential veto. The distinction matters:

- The assigned reviewer holds **Agree** — they can block a merge.
- Other commenters are providing **Input** — their feedback should be
  considered but does not block the decision.

The feature owner is responsible for synthesizing Input and deciding what to act
on. Disagreements that cannot be resolved between the PR author and reviewer
should be escalated via the process below, not left open indefinitely.

For review mechanics (when to use Request Changes vs. Comment), see [How We Use
GitHub — Code Review and Merging][how-we-use-github].

## Escalation Process

Conda-maintainers follows the IETF's principle of rough consensus ([RFC
7282][rfc7282]). This shapes how we handle disagreements: the goal is not for
everyone to be happy, and not a majority vote. The goal is that all technical
objections have been genuinely heard and either addressed or determined not to
be blockers.

> "Consensus is when everyone is sufficiently satisfied with the chosen
> solution, such that they no longer have specific objections to it." — RFC 7282

Two things that are **not** rough consensus:

- A minority objector simply giving up and saying "do what you want" — that is
  capitulation, not consensus. An unaddressed technical objection is still an
  open issue.
- Horse-trading: "I'll drop my objection if you drop yours." This leaves both
  issues unresolved.

If a PR author and reviewer cannot reach agreement after good-faith discussion,
either party may call an escalation meeting with the conda-maintainers team.

### Step 1 — Reframe objections on the PR

Before calling a meeting, the party with the objection should post a comment
that clearly states:

- The specific technical concern (not a preference or style opinion)
- What outcome would address it

This separates genuine blockers from unappealing-but-acceptable tradeoffs. If the
objection is that the solution is not ideal but workable, that is not a blocker
— rough consensus has been reached.

### Step 2 — Signal the impasse and schedule a meeting

If the objection remains unresolved after Step 1, either party adds a comment on
the PR stating the review is at an impasse. The person calling the meeting opens
a thread in `#conda-maintainers` on Zulip with:

- A link to the PR
- A one-sentence neutral summary of the unresolved technical question

Tag `@conda-maintainers` and coordinate a meeting time that works for the team
while being considerate of global time-zones. The feature owner attends if the
PR is part of an active feature.

### Step 3 — Hold the meeting

The meeting facilitator (typically the feature owner, or the most senior
maintainer present) should:

- Ask each party to state their technical objection specifically, not re-argue
  the full history
- For each objection, ask: "Has this concern been addressed, or is it a genuine
  technical blocker?"
- Distinguish between objections that need to be resolved and preferences that
  can be set aside
- Declare rough consensus when all technical blockers have been addressed, even
  if not everyone prefers the chosen solution

The facilitator does not need unanimity to declare rough consensus. A strong
majority with no unaddressed technical blockers is sufficient.

### Step 4 — Record the outcome on the PR

Whoever called the meeting posts a comment on the PR summarising the decision
and the reasoning — specifically noting how any technical objections were
addressed or why they were determined not to be blockers. The PR then proceeds
accordingly.

## Further Reading

- [conda governance][governance] — Project Team membership, voting procedures
- [RAPID Approach][rapid] — Background on the Recommend, Agree, Perform, Input, Decide roles
- [Contributing](contributing) — PR and code review process
- [How We Use GitHub — Code Review and Merging][how-we-use-github] — GitHub
  workflow and review requirements
