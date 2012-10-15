

# the package names we use are always of the form <name>-<version>-<build>,
# where the name may contains one or more '-' characters.
# the build number is always a positive integer value.

def split_req_string(req_string):
    '''
    Split a requirement string into (name, version) or (name, version, build) tuples.

    Parameters
    ----------
    req_string : str
               string containing a package name and version separated by a space

    >>> split_req_string('python 2.7')
    ('python', '2.7')
    >>>

    '''
    space_split = req_string.split()
    if len(space_split) in [2,3]:
        return tuple(space_split)

    eq_split = req_string.split('=')
    if len(eq_split) in [2,3]:
        return tuple(eq_split)

    raise RuntimeError("Cannot split string '%s' into requirement components" % req_string)

def split_canonical_name(pkg_name):
    '''
    Split a canonical package name into (name, version, build) strings.

    Parameters
    ----------
    pkg_name : str
             string containing package name, version, and build string separated by dashes

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

    >>> parse_package_filename('anaconda-1.1-np17py27_ce0.tar.bz2')
    ('anaconda', '1.1', 'np17py27_ce0')
    >>>

    '''
    try:
        pkg_name = get_canonical_name(pkg_filename)
        return split_canonical_name(pkg_name)
    except:
        raise RuntimeError("Could not parse package filename '%s'" % pkg_filename)


