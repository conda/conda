'''
This module is for backwards compatibility with the Launcher. All
functions contained are deprecated and should not be usd for any
new development.
'''


from anaconda import anaconda


def get_all_deps():
    conda = anaconda()
    res = {}
    for pkg in conda.pkgs:
        res[pkg.canonical_name] = list()
        for req in pkg.requires:
            req_string = "%s-%s-none" % (req.name, req.version.vstring)
            res[pkg.canonical_name].append(req_string)

    return res


def get_deps(pkgs):
    all_deps = get_all_deps()
    if isinstance(pkgs, str):
        return all_deps[pkgs]
    deps = set([])
    for pkg in pkgs:
        deps = deps.union(set(all_deps[pkg]))
    return sorted(list(deps))


def get_all_reverse_deps():
    res = {}
    deps = get_all_deps()
    for k,v in deps.items():
        for p in v:
            if p not in res:
                res[p] = []
            res[p].append(k)
    return res


def get_reverse_deps(pkgs):
    all_rdeps = get_all_reverse_deps()
    if isinstance(pkgs, str):
        return all_rdeps[pkgs]
    rdeps = set([])
    for pkg in pkgs:
        rdeps = rdeps.union(set(all_rdeps[pkg]))
    return sorted(list(rdeps))