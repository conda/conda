"""
The basic idea to nest logical expressions is instead of trying to denest
things via distribution, we add new variables. So if we have some logical
expression expr, we replace it with x and add expr <-> x to the clauses,
where x is a new variable, and expr <-> x is recursively evaluated in the
same way, so that the final clauses are ORs of atoms.

All functions return the tuple (new_var, new_clauses). new_var is a literal
that should be used in place of the expression, or true or false, which are
custom objects defined in this module, which means that the expression is
identically true or false. new_clauses should be added to the clauses of the
SAT solver.

All functions take atoms as arguments (an atom is an integer, representing a
literal or a negated literal, or the true or false objects defined in this
module), that is, it is the callers' responsibility to do the conversion of
expressions recursively. This is done because we do not have data structures
representing the various logical classes, only atoms.

"""
from collections import defaultdict

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


# Custom classes for true and false. Using True and False is too risky, since
# True == 1, so it might be confused for the literal 1.
class TrueClass(object):
    def __eq__(self, other):
        return isinstance(other, TrueClass)

    def __neg__(self):
        return false

    def __str__(self):
        return "true"
    __repr__ = __str__

class FalseClass(object):
    def __eq__(self, other):
        return isinstance(other, FalseClass)

    def __neg__(self):
        return true

    def __str__(self):
        return "false"
    __repr__ = __str__

true = TrueClass()
false = FalseClass()

# TODO: Take advantage of polarity, meaning that we can add only one direction
# of the implication, expr -> x or expr <- x, depending on how expr appears.

# Code that uses special cases (generates no clauses) is in ADTs/FEnv.h in
# minisatp. Code that generates clauses is in Hardware_clausify.cc (and are
# also described in the paper, "Translating Pseudo-Boolean Constraints into
# SAT," Eén and Sörensson).

def ITE(c, t, f):
    """
    if c then t else f

    In this function, if any of c, t, or f are True and False the resulting
    expression is resolved.
    """
    if c == true:
        return (t, [])
    if c == false:
        return (f, [])
    if t == f:
        return (t, [])
    if t == -f:
        return Xor(c, f)
    if t == false or t == -c:
        return And(-c, f)
    if t == true or t == c:
        return Or(c, f)
    if f == false or f == c:
        return And(c, t)
    if f == true or f == -c:
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

def And(f, g):
    if f == false or g == false:
        return (false, [])
    if f == true:
        return (g, [])
    if g == true:
        return (f, [])
    if f == g:
        return (f, [])
    if f == -g:
        return (false, [])

    # if g < f:
    #     swap(f, g)

    x = get_new_var()
    clauses = [
        # positive
        # ~f -> ~x, ~g -> ~x
        [-x, f],
        [-x, g],
        # negative
        # (f AND g) -> x
        [x, -f, -g],
        ]
    return (x, clauses)


def Or(f, g):
    x, clauses = And(-f, -g)
    return (-x, clauses)

def Xor(f, g):
    # Minisatp treats XOR as NOT EQUIV
    if f == false:
        return (g, [])
    if f == true:
        return (-g, [])
    if g == false:
        return (f, [])
    if g == true:
        return (-f, [])
    if f == g:
        return (false, [])
    if f == -g:
        return (true, [])

    # if g < f:
    #     swap(f, g)

    x = get_new_var()
    clauses = [
        # Positive
        [-x, f, g],
        [-x, -f, -g],
        # Negative
        [x, -f, g],
        [x, f, -g],
        ]
    return (x, clauses)

def build_BDD(linear, sum=0, material_left=None):
    if not material_left:
        material_left = linear.total
    clauses = []
    lower_limit = linear.lo - sum
    upper_limit = linear.hi - sum
    if lower_limit <= 0 and upper_limit >= material_left:
        return (true, clauses)
    if lower_limit > material_left or upper_limit < 0:
        return (false, clauses)

    new_linear = linear[:-1]
    LC = linear.coeffs[-1]
    LA = linear.atoms[-1]
    material_left -= linear.coeffs[-1]
    # This is handled by the abs() call below. I think it's done this way to
    # aid caching.
    hi_sum = sum if LA < 0 else sum + LC
    lo_sum = sum + LC if LA < 0 else sum
    hi, new_clauses = build_BDD(new_linear, hi_sum, material_left)
    clauses += new_clauses
    lo, new_clauses = build_BDD(new_linear, lo_sum, material_left)
    clauses += new_clauses
    ret, new_clauses = ITE(abs(LA), hi, lo)
    clauses += new_clauses

    return ret, clauses

class Linear(object):
    """
    A (canonicalized) linear constraint

    Canonicalized means all coefficients are positive.
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
        self.atom2coeff = defaultdict(int, {atom: coeff for coeff, atom in self.equation})
        # self.lower_limit = self.lo - self.total
        # self.upper_limit = self.hi - self.total

    def __call__(self, sol):
        """
        Call a solution to see if it is satisfied
        """
        t = 0
        for s in sol:
            t += self.atom2coeff[s]
        return self.lo <= t <= self.hi

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
