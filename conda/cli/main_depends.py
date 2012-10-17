
from optparse import OptionParser
from os.path import abspath, expanduser

def main_depends(args, conda, display_help=False):
    p = OptionParser(
        usage       = "usage: conda depends [options] packages",
        description = "Query Anaconda package dependencies.",
    )
    p.add_option(
        '-r', "--reverse",
        action  = "store_true",
        default = False,
        help    = "generate reverse dependencies",
    )
    p.add_option(
        '-v', "--verbose",
        action  = "store_true",
        default = False,
        help    = "display build strings on reverse dependencies"
    )
    p.add_option(
        '-m', "--max-depth",
        action  = "store",
        type    = "int",
        default = None,
        help    = "maximum depth to search dependencies, defaults to searching all depths (0 also searchs all depths)",
    )
    p.add_option(
        '-p', "--prefix",
        action  = "store",
        default = conda.root_dir,
        help    = "return dependencies compatible with a specified environment, defaults to %default",
    )
    p.add_option(
        '-n', "--no-prefix",
        action  = "store_true",
        default = False,
        help    = "return reverse dependencies compatible with any specified environment, overrides --prefix",
    )


    if display_help:
        p.print_help()
        return

    opts, args = p.parse_args(args)

    if len(args) == 0:
        p.error('too few arguments')

    prefix = abspath(expanduser(opts.prefix))
    env = conda.lookup_environment(prefix)

    pkgs = [env.find_activated_package(arg) for arg in args]

    if opts.reverse:
        reqs = conda.index.find_compatible_requirements(pkgs)
        rdeps = conda.index.get_reverse_deps(reqs, opts.max_depth)

        fmt = '%s' if len(args) == 1 else '{%s}'

        if len(rdeps) == 0:
            print 'No packages depend on ' + fmt % ', '.join(args)
            return

        if not opts.no_prefix:
            rdeps = rdeps & env.activated

        if opts.verbose:
            names = sorted([pkg.canonical_name for pkg in rdeps])
        else:
            names = [str(pkg) for pkg in rdeps]
            names_count = dict((k, names.count(k)) for k in names)
            names = sorted(list(set(names)))

        activated = '' if opts.no_prefix else 'activated '
        print 'The following %spackages depend on ' % activated + fmt % ', '.join(args) + ':'
        for name in names:
            if opts.verbose or names_count[name]==1:
                print '    %s' % name
            else:
                print '    %s (%d builds)' % (name, names_count[name])

    else:
        deps = conda.index.get_deps(pkgs, opts.max_depth)

        if len(deps) == 0:
            suffix, fmt = ('es', '%s') if len(args) == 1 else ('', '{%s}')
            print (fmt + ' do%s not depend on any packages') % (', '.join(args), suffix)
            return

        names = sorted(['%s %s' % (dep.name, dep.version.vstring) for dep in deps])

        suffix, fmt = ('s', '%s') if len(args) == 1 else ('', '{%s}')
        print (fmt + ' depend%s on the following packages:') % (', '.join(args), suffix)
        for name in names:
            print '    %s' % name

