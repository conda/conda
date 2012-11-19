

# the package names we use are always of the form <name>-<version>-<build>,
# where the name may contains one or more '-' characters.
# the build number is always a positive integer value.

def split_spec_string(spec_string):
    '''
    Split a package specification string into (name, version) or (name, version, build) tuples.

    Parameters
    ----------
    spec_string : str
        string containing a package name and version separated by a space, or by '='

    Examples
    --------
    >>> split_spec_string('python 2.7')
    ('python', '2.7')
    >>>

    Raises
    ------
    RuntimeError
        if the spec_string cannot be meaningfully split

    '''
    space_split = spec_string.split()
    eq_split = spec_string.split('=')

    if len(space_split) > 3 or len(eq_split) > 3:
        raise RuntimeError("Cannot split string '%s' into package spec components" % spec_string)

    if len(space_split) > 1 and len(eq_split) > 1:
        raise RuntimeError("Cannot split string '%s' into package spec components" % spec_string)

    if len(space_split) > len(eq_split):
        return tuple(space_split)
    else:
        return tuple(eq_split)


def split_canonical_name(pkg_name):
    '''
    Split a canonical package name into (name, version, build) strings.

    Parameters
    ----------
    pkg_name : str
        string containing package name, version, and build string separated by dashes

    Examples
    --------
    >>> split_canonical_name('anaconda-1.1-np17py27_ce0')
    ('anaconda', '1.1', 'np17py27_ce0')
    >>>

    '''
    return tuple(pkg_name.rsplit('-', 2))

def get_canonical_name(pkg_filename):
    '''
    Return a canonical name from a package filename.

    Parameters
    ----------
    pkg_filename : str
        string containing a package name, version and build string separated by dashes,
        as well as a '.tar.bz2' extension

    Examples
    --------
    >>> get_canonical_name('anaconda-1.1-np17py27_ce0.tar.bz2')
    'anaconda-1.1-np17py27_ce0'
    >>>

    '''
    return pkg_filename[:-8]

def parse_package_filename(pkg_filename):
    '''
    Parse a package filename into (name, version, build) strings.

    Parameters
    ----------
    pkg_filename : str
        string containing a package name, version and build string separated by dashes,
        as well as a '.tar.bz2' extension

    Examples
    --------
    >>> parse_package_filename('anaconda-1.1-np17py27_ce0.tar.bz2')
    ('anaconda', '1.1', 'np17py27_ce0')
    >>>

    '''
    try:
        pkg_name = get_canonical_name(pkg_filename)
        return split_canonical_name(pkg_name)
    except:
        raise RuntimeError("Could not parse package filename '%s'" % pkg_filename)


