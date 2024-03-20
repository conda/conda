---
title: "{{ env.TITLE }} ({{ date | date("YYYY-MM-DD") }})"
labels: [type::bug, type::testing]
---

The {{ workflow }} workflow failed on {{ date | date("YYYY-MM-DD HH:mm") }} UTC

Full run: https://github.com/conda/conda/actions/runs/{{ env.RUN_ID }}

(This post will be updated if another test fails today, as long as this issue remains open.)
