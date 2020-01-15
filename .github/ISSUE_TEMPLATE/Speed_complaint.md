---
name: Speed complaint
about: If you think conda is going too slow

---


<!--
Hi!  Read this; it's important.

Anaconda Community Code of Conduct: https://www.anaconda.com/community-code-of-conduct/

We get a lot of reports on the conda issue tracker about speed. These are mostly
not very helpful, because they only very generally complain about the total time
conda is taking. They often don’t even say what conda is taking so long to do -
just that it’s slow. If you want to file an issue report about conda’s speed, we
ask that you take the time to isolate exactly what part is slow, and what you think
is a reasonable amount of time for that operation to take (preferably by
comparison with another tool that is performing a similar task). Please see some
tips below on how to collect useful information for a bug report.

Complaints that include no useful information will be ignored and closed.

-->

## Steps to Reproduce
<!-- Show us some debugging output.  Here we generate conda_debug_output.txt - please upload it with your report.

* On unix (bash shells): 

  CONDA_INSTRUMENTATION_ENABLED=1 <your conda command> -vv | tee conda_debug_output.txt

* On Windows:

  set CONDA_INSTRUMENTATION_ENABLED=1
  powershell "<your conda command> -vv | tee conda_debug_output.txt"

-->
```
< paste conda_debug_output.txt here, or attach it as a file to this report >

```

```
< paste contents of ~/.conda/instrumentation-record.csv here, or attach it as a file to this report >
```


## Environment Information
<details open><summary><code>`conda info`</code></summary><p>
<!-- between the ticks below, paste the output of 'conda info' -->

```

```
</p></details>


<details open><summary><code>`conda config --show-sources`</code></summary><p>
<!-- between the ticks below, paste the output of 'conda config --show-sources' -->

```

```
</p></details>


<details><summary><code>`conda list --show-channel-urls`</code></summary><p>
<!-- between the ticks below, paste the output of 'conda list --show-channel-urls' -->

```

```
</p></details>
