# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import re
from subprocess import check_output

output = check_output('(git log --format="%aN <%aE>"; git log --format="%cN <%cE>") | sort -u', shell=True)
output = output.decode("utf-8").strip().split('\n')
contributors = set(line.strip() for line in output)
contributors.remove("GitHub <noreply@github.com>")

with open('.cla-signers') as fh:
    cla_signer_lines = (line for line in fh.read().strip().split('\n') if '|' in line)
    cla_signers = set(line.split('|')[1].strip() for line in cla_signer_lines)

missing_signatures = contributors - cla_signers


with open('.exempt-commits') as fh:
    exempt_commits_lines = tuple(line for line in fh.read().strip().split('\n') if '|' in line)
    exempt_commits = set(line.split('|')[0].strip() for line in exempt_commits_lines)

with open('.github-map') as fh:
    github_map = dict(
        (git_id.strip(), ghusername.strip()) for ghusername, git_id in
        (line.split("|") for line in fh.read().strip().split('\n') if '|' in line)
    )


# git log --format="%aN <%aE>" | awk '{ ++c[$0]; } END { for(cc in c) printf "%5d %s\n",c[cc],cc; }' | sort -r
output = check_output('git log --format="%aN <%aE>" | awk \'{ ++c[$0]; } END { for(cc in c) printf "%5d %s\\n",c[cc],cc; }\' | sort -r', shell=True)
output = output.decode("utf-8").strip().split('\n')
contributions = tuple((git_id, commits) for commits, git_id in (line.strip().split(' ', 1) for line in output) if git_id in missing_signatures)
contributions_map = dict((git_id, int(commits)) for commits, git_id in (line.strip().split(' ', 1) for line in output) if git_id in missing_signatures)


missing_signatures_stats = {}
for git_id in missing_signatures:
    output = check_output('git log --author="{0}" --use-mailmap --format="%H" --shortstat'.format(git_id), shell=True)
    output = output.decode("utf-8").strip()
    groups = re.findall(r"(?:(^[0-9a-f]{40})\n)(?:\n \d+ files? changed(?:, (\d+) insertions?\(\+\))?(?:, (\d+) deletion)?)?", output, re.MULTILINE)
    commits = insertions = deletions = 0
    hashes = []
    for group in groups:
        if group[0] in exempt_commits:
            continue
        commits += 1
        hashes.append(group[0])
        insertions += int(group[1] or 0)
        deletions += int(group[2] or 0)
    if not hashes:
        continue
    missing_signatures_stats[git_id] = (len(hashes), insertions, deletions, hashes)

for git_id in sorted(missing_signatures_stats, key=lambda x: (missing_signatures_stats[x][0], missing_signatures_stats[x][1]), reverse=True):
    stats = missing_signatures_stats[git_id]
    print("%-18s%-63s%4s%4s%4s" % (github_map[git_id], git_id, stats[0], stats[1], stats[2]))



print()
print("missing signatures", len(missing_signatures_stats))
print("total commits", sum(x[0] for x in missing_signatures_stats.values()))
print("total additions", sum(x[1] for x in missing_signatures_stats.values()))
print()


for git_id in sorted(missing_signatures_stats, key=lambda x: (missing_signatures_stats[x][0], missing_signatures_stats[x][1]), reverse=True):
    print("\n===============================================================")
    print("===============================================================\n\n")
    stats = missing_signatures_stats[git_id]
    print("%-73s%4s%4s%4s" % (git_id, stats[0], stats[1], stats[2]))

    for sha in stats[3]:
        print("  %s" % sha)

    output = check_output('git show {0}'.format(" ".join(stats[3])), shell=True)
    print(output.decode("utf-8").strip())
