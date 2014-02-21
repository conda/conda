"""
The basic idea to nest logical expressions is instead of trying to denest
things via distribution, we add new variables. So if we have some logical
expression expr, we replace it with x and add expr <-> x to the clauses,
where x is a new variable, and expr <-> x is recursively evaluated in the
same way, so that the final clauses are ORs of atoms.

To us this, create a new Clauses object with the max var, for instance, if you
already have [[1, 2, -3]], you would use C = Clause(3).  All functions return
a new literal, which represents that function, or true or false, which are
custom objects defined in this module, which means that the expression is
identically true or false.. They may also add new clauses to C.clauses, which
should be added to the clauses of the SAT solver.

All functions take atoms as arguments (an atom is an integer, representing a
literal or a negated literal, or the true or false objects defined in this
module), that is, it is the callers' responsibility to do the conversion of
expressions recursively. This is done because we do not have data structures
representing the various logical classes, only atoms.

"""
from collections import defaultdict

from conda.utils import memoize

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

    def __hash__(self):
        return 1

class FalseClass(object):
    def __eq__(self, other):
        return isinstance(other, FalseClass)

    def __neg__(self):
        return true

    def __str__(self):
        return "false"
    __repr__ = __str__

    def __hash__(self):
        return 0

true = TrueClass()
false = FalseClass()

# TODO: Take advantage of polarity, meaning that we can add only one direction
# of the implication, expr -> x or expr <- x, depending on how expr appears.

# Code that uses special cases (generates no clauses) is in ADTs/FEnv.h in
# minisatp. Code that generates clauses is in Hardware_clausify.cc (and are
# also described in the paper, "Translating Pseudo-Boolean Constraints into
# SAT," Eén and Sörensson).

class Clauses(object):
    def __init__(self, MAX_N=0):
        self.clauses = set()
        self.MAX_N = MAX_N

    def get_new_var(self):
        self.MAX_N += 1
        return self.MAX_N

    @memoize
    def ITE(self, c, t, f):
        """
        if c then t else f

        In this function, if any of c, t, or f are True and False the resulting
        expression is resolved.
        """
        if c == true:
            return t
        if c == false:
            return f
        if t == f:
            return t
        if t == -f:
            return self.Xor(c, f)
        if t == false or t == -c:
            return self.And(-c, f)
        if t == true or t == c:
            return self.Or(c, f)
        if f == false or f == c:
            return self.And(c, t)
        if f == true or f == -c:
            return self.Or(t, -c)

        # TODO: At this point, minisatp has
        # if t < f:
        #     swap(t, f)
        #     c = -c

        # Basically, c ? t : f is equivalent to (c AND t) OR (NOT c AND f)
        x = self.get_new_var()
        # "Red" clauses are redundant, but they assist the unit propagation in the
        # SAT solver
        self.clauses |= {
            # Negative
            (-c, -t, x),
            (c, -f, x),
            (-t, -f, x), # Red
            # Positive
            (-c, t, -x),
            (c, f, -x),
            (t, f, -x), # Red
        }

        return x

    @memoize
    def And(self, f, g):
        if f == false or g == false:
            return false
        if f == true:
            return g
        if g == true:
            return f
        if f == g:
            return f
        if f == -g:
            return false

        # if g < f:
        #     swap(f, g)

        x = self.get_new_var()
        self.clauses |= {
            # positive
            # ~f -> ~x, ~g -> ~x
            (-x, f),
            (-x, g),
            # negative
            # (f AND g) -> x
            (x, -f, -g),
            }

        return x


    @memoize
    def Or(self, f, g):
        return -self.And(-f, -g)

    @memoize
    def Xor(self, f, g):
        # Minisatp treats XOR as NOT EQUIV
        if f == false:
            return g
        if f == true:
            return -g
        if g == false:
            return f
        if g == true:
            return -f
        if f == g:
            return false
        if f == -g:
            return true

        # if g < f:
        #     swap(f, g)

        x = self.get_new_var()
        self.clauses |= {
            # Positive
            (-x, f, g),
            (-x, -f, -g),
            # Negative
            (x, -f, g),
            (x, f, -g),
            }
        return x

    @memoize
    def build_BDD(self, linear, sum=0):
        lower_limit = linear.lo - sum
        upper_limit = linear.hi - sum
        if lower_limit <= 0 and upper_limit >= linear.total:
            return true
        if lower_limit > linear.total or upper_limit < 0:
            return false

        new_linear = linear[:-1]
        LC = linear.coeffs[-1]
        LA = linear.atoms[-1]
        # This is handled by the abs() call below. I think it's done this way to
        # aid caching.
        hi_sum = sum if LA < 0 else sum + LC
        lo_sum = sum + LC if LA < 0 else sum
        hi = self.build_BDD(new_linear, hi_sum)
        lo = self.build_BDD(new_linear, lo_sum)
        ret = self.ITE(abs(LA), hi, lo)

        return ret

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

    def __hash__(self):
        hashable_equation = tuple([tuple([i for i in term]) for term in
            self.equation])
        return hash((hashable_equation, self.lo, self.hi))

    def __str__(self):
        return "Linear(%r, %r)" % (self.equation, self.rhs)

    __repr__ = __str__
