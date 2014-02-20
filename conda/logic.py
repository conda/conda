"""
The basic idea to nest logical expressions is instead of trying to denest
things via distribution, we add new variables. So if we have some logical
expression expr, we replace it with x and add expr <-> x to the clauses,
where x is a new variable, and expr <-> x is recursively evaluated in the
same way, so that the final clauses are ORs of atoms.
"""

# Global state? Really?

global MAX_N
MAX_N = 0

def get_new_var():
    global MAX_N
    new_var = MAX_N = MAX_N + 1
    return new_var

def set_max_var(m):
    global MAX_N
    MAX_N = m

# All functions return the tuple (new_var, new_clauses). new_var is a literal
# that should be used in place of the expression. new_clauses should be added
# to the clauses of the SAT solver.

# All functions take atoms as arguments, that is, it is the callers'
# responsibility to do the conversion of expressions recursively. This is done
# because we do not have data structures representing the various logical
# classes, only atoms.


# TODO: Take advantage of polarity, meaning that we can add only one direction
# of the implication, expr -> x or expr <- x, depending on how expr appears.

def ITE(c, t, f):
    """
    if c then t else f

    In this function, if any of c, t, or f are True and False the resulting
    expression is resolved.
    """
    # Translated from ATDS/FEnv.h in minisatp

    # Note: It's important to use "is True", not "== True", because True == 1
    if c is True:
        return (t, [])
    if c is False:
        return (f, [])
    # Be careful with the atom "1"
    if t == f and not isinstance(f, bool) and not isinstance(t, bool):
        return (t, [])
    if t == -f and not isinstance(f, bool) and not isinstance(t, bool):
        return Xor(c, f)
    if t is False or t == -c:
        return And(-c, f)
    if t is True or t == c:
        return Or(c, f)
    if f is False or f == c:
            return And(c, t)
    if f is True or f == -c:
        return Or(t, -c)

    # TODO: At this point, minisatp has
    # if t < f:
    #     swap(t, f)
    #     c = -c

    # Basically, c ? t : f is equivalent to (c AND t) OR (NOT c AND f)
    x = get_new_var()
    # "Red" clauses are redundant, but they assist the unit propagation in the
    # SAT solver
    new_clauses = [
        # Negative
        [-c, -t, x],
        [c, -f, x],
        [-t, -f, x], # Red
        # Positive
        [-c, t, -x],
        [c, f, -x],
        [t, f, -x], # Red
    ]

    return (x, new_clauses)

def And(a, b):
    raise NotImplementedError

def Or(a, b):
    raise NotImplementedError

def Xor(a, b):
    raise NotImplementedError

def build_BDD(linear, material_left, max_cost):
    pass

class Linear(object):
    """
    A (canonicalized) linear constraint

    Canonicalized means all coefficients are positive and the constraint is <=.
    """
    def __init__(self, equation, rhs):
        """
        Equation should be a list of tuples of the form (coeff, atom). rhs is
    the number on the right-hand side, or a list [lo, hi].
        """
        self.equation = sorted(equation)
        self.rhs = rhs
        if isinstance(rhs, int):
            self.lo = self.hi = rhs
        else:
            self.lo, self.hi = rhs
        self.coeffs = []
        self.atoms = []
        for coeff, atom in self.equation:
            self.coeffs.append(coeff)
            self.atoms.append(atom)
        self.total = sum([i for i, _ in equation])
        self.lower_limit = self.lo - self.total
        self.upper_limit = self.hi - self.total

    def __len__(self):
        return len(self.equation)

    def __getitem__(self, key):
        if not isinstance(key, slice):
            raise NotImplementedError("Non-slice indices are not supported")
        return self.__class__(self.equation.__getitem__(key), self.rhs)

    def __eq__(self, other):
        if not isinstance(other, Linear):
            return False
        return (self.equation == other.equation and self.lo == other.lo and
        self.hi == other.hi)

    def __str__(self):
        return "Linear(%r, %r)" % (self.equation, self.rhs)

    __repr__ = __str__
