# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

from subprocess import check_output


contributors = sorted(set(x.strip('"') for x in check_output(
    ['git', 'log', '--format="%aN <%aE>"']
).decode("utf-8").splitlines()))


with open('.cla-signers') as fh:
    github_map_lines = fh.read().strip().split('\n')


def get_cla_signers():
    with open('.cla-signers') as fh:
        for line in fh:
            line = line.strip()
            if line.startswith('#') or not line:
                continue
            yield line

signers_map = {}

for line in get_cla_signers():
    username, contributor_name, _ = line.split('|')
    username = username.strip()
    contributor_name = contributor_name.strip()
    if username:
        signers_map[contributor_name] = username



def get_github_map_line():
    with open('.github-map') as fh:
        for line in fh:
            line = line.strip()
            if line.startswith('#') or not line:
                continue
            github_username, git_id = line.split('|')
            yield git_id.strip(), github_username.strip()


github_username_map = dict(x for x in get_github_map_line())

sent = [
    "alanhdu",
    "arkottke",
    "almarklein",
    "groutr",
    "delicb",
    "chrislf",
    "dan-blanchard",
    "Horta",
    "dhirschfeld",
    "dfroger",
    "dawehner",
    "dedalusj",
    "e-gillies-ix",
    "3kwa",
    "faph",
    "flaviomartins",
    "aldanor",
    "jacoblsmith",
    "jrovegno",
    "jbcrail",
    "jerowe",
    "kdeldycke",
    "Korijn",
    "mikecroucher",
    "blindgaenger",
    "mdengler",
    "melund",
    "megies",
    "mheilman",
    "elehcim",
    "mika-fischer",
    "natefoo",
    "nickeubank",
    "rcthomas",
    "remram44",
    "rleecivis",
    "tdhopper",
    "twiecki",
    "tpn",
    "ukoethe",
    "esc",
    "NewbiZ",
    "wojdyr",
    "wulmer",
]



for contributor in contributors:
    if contributor not in signers_map:
        github_username = github_username_map[contributor]
        if github_username not in sent:
            print(contributor)



