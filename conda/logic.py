# -*- coding: utf-8 -*-
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

The polarity argument can be set to True or False if you know that the literal
being used will only be used in the positive or the negative, respectively
(e.g., you will only use x, not -x).  This will generate fewer clauses.

"""
from collections import defaultdict
from functools import total_ordering
import logging
import pycosat

from conda.compat import log2, ceil, zip
from conda.utils import memoize

dotlog = logging.getLogger('dotupdate')
log = logging.getLogger(__name__)

# Custom classes for true and false. Using True and False is too risky, since
# True == 1, so it might be confused for the literal 1.
@total_ordering
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

    def __lt__(self, other):
        if isinstance(other, TrueClass):
            return False
        if isinstance(other, FalseClass):
            return False
        return NotImplemented

@total_ordering
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

    def __lt__(self, other):
        if isinstance(other, FalseClass):
            return False
        if isinstance(other, TrueClass):
            return True
        return NotImplemented

true = TrueClass()
false = FalseClass()

# Code that uses special cases (generates no clauses) is in ADTs/FEnv.h in
# minisatp. Code that generates clauses is in Hardware_clausify.cc (and are
# also described in the paper, "Translating Pseudo-Boolean Constraints into
# SAT," Eén and Sörensson).  The sorter code is in Hardware_sorters.cc.

class Clauses(object):
    def __init__(self, MAX_N=0):
        self.clauses = set()
        self.MAX_N = MAX_N

    def get_new_var(self):
        self.MAX_N += 1
        return self.MAX_N

    @memoize
    def ITE(self, c, t, f, polarity=None, red=True):
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
            return self.Xor(c, f, polarity=polarity)
        if t == false or t == -c:
            return self.And(-c, f, polarity=polarity)
        if t == true or t == c:
            return self.Or(c, f)
        if f == false or f == c:
            return self.And(c, t, polarity=polarity)
        if f == true or f == -c:
            return self.Or(t, -c)

        if t < f:
            t, f = f, t
            c = -c

        # Basically, c ? t : f is equivalent to (c AND t) OR (NOT c AND f)
        x = self.get_new_var()
        # "Red" clauses are redundant, but they assist the unit propagation in the
        # SAT solver
        if polarity in {False, None}:
            self.clauses |= {
                # Negative
                (-c, -t, x),
                (c, -f, x),
                }
            if red:
                self.clauses |= {
                    (-t, -f, x), # Red
                }
        if polarity in {True, None}:
            self.clauses |= {
                # Positive
                (-c, t, -x),
                (c, f, -x),
                }
            if red:
                self.clauses |= {
                    (t, f, -x), # Red
                }

        return x

    @memoize
    def And(self, f, g, polarity=None):
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

        if g < f:
            f, g = g, f

        x = self.get_new_var()
        if polarity in {True, None}:
            self.clauses |= {
                # positive
                # ~f -> ~x, ~g -> ~x
                (-x, f),
                (-x, g),
                }
        if polarity in {False, None}:
            self.clauses |= {
            # negative
            # (f AND g) -> x
            (x, -f, -g),
            }

        return x

    @memoize
    def Or(self, f, g, polarity=None):
        if polarity is not None:
            polarity = not polarity
        return -self.And(-f, -g, polarity=polarity)

    @memoize
    def Xor(self, f, g, polarity=None):
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

        if g < f:
            f, g = g, f

        x = self.get_new_var()
        if polarity in {True, None}:
            self.clauses |= {
                # Positive
                (-x, f, g),
                (-x, -f, -g),
            }
        if polarity in {False, None}:
            self.clauses |= {
                # Negative
                (x, -f, g),
                (x, f, -g),
            }
        return x

    # Memoization is done in the function itself
    # TODO: This is a bit slower than the recursive version because it doesn't
    # "jump back" to the call site.
    def build_BDD(self, linear, sum=0, polarity=None):
        call_stack = [(linear, sum)]
        first_stack = call_stack[0]
        ret = {}
        while call_stack:
            linear, sum = call_stack[-1]
            lower_limit = linear.lo - sum
            upper_limit = linear.hi - sum
            if lower_limit <= 0 and upper_limit >= linear.total:
                ret[call_stack.pop()] = true
                continue
            if lower_limit > linear.total or upper_limit < 0:
                ret[call_stack.pop()] = false
                continue

            new_linear = linear[:-1]
            LC = linear.LC
            LA = linear.LA
            # This is handled by the abs() call below. I think it's done this way to
            # aid caching.
            hi_sum = sum if LA < 0 else sum + LC
            lo_sum = sum + LC if LA < 0 else sum
            try:
                hi = ret[(new_linear, hi_sum)]
            except KeyError:
                call_stack.append((new_linear, hi_sum))
                continue

            try:
                lo = ret[(new_linear, lo_sum)]
            except KeyError:
                call_stack.append((new_linear, lo_sum))
                continue

            ret[call_stack.pop()] = self.ITE(abs(LA), hi, lo, polarity=polarity)

        return ret[first_stack]

    # Reference implementation for testing. The recursion depth gets exceeded
    # for too long formulas, so we use the non-recursive version above.
    @memoize
    def build_BDD_recursive(self, linear, sum=0, polarity=None):
        lower_limit = linear.lo - sum
        upper_limit = linear.hi - sum
        if lower_limit <= 0 and upper_limit >= linear.total:
            return true
        if lower_limit > linear.total or upper_limit < 0:
            return false

        new_linear = linear[:-1]
        LC = linear.LC
        LA = linear.LA
        # This is handled by the abs() call below. I think it's done this way to
        # aid caching.
        hi_sum = sum if LA < 0 else sum + LC
        lo_sum = sum + LC if LA < 0 else sum
        hi = self.build_BDD_recursive(new_linear, hi_sum, polarity=polarity)
        lo = self.build_BDD_recursive(new_linear, lo_sum, polarity=polarity)
        ret = self.ITE(abs(LA), hi, lo, polarity=polarity)

        return ret

    @memoize
    def Cmp(self, a, b):
        """
        Returns [max(a, b), min(a, b)].
        """
        return [self.Or(a, b), self.And(a, b)]

    def odd_even_mergesort(self, A):
        if len(A) == 1:
            return A
        if int(log2(len(A))) != log2(len(A)): # accurate to about 2**48
            raise ValueError("Length of list must be a power of 2 to odd-even merge sort")

        evens = A[::2]
        odds = A[1::2]
        sorted_evens = self.odd_even_mergesort(evens)
        sorted_odds = self.odd_even_mergesort(odds)
        return self.odd_even_merge(sorted_evens, sorted_odds)

    def odd_even_merge(self, A, B):
        if len(A) != len(B):
            raise ValueError("Lists must be of the same length to odd-even merge")
        if len(A) == 1:
            return self.Cmp(A[0], B[0])

        # Guaranteed to have the same length because len(A) is a power of 2
        A_evens = A[::2]
        A_odds = A[1::2]
        B_evens = B[::2]
        B_odds = B[1::2]
        C = self.odd_even_merge(A_evens, B_odds)
        D = self.odd_even_merge(A_odds, B_evens)
        merged = []
        for i, j in zip(C, D):
            merged += self.Cmp(i, j)

        return merged

    def build_sorter(self, linear):
        if not linear:
            return []
        sorter_input = []
        for coeff, atom in linear.equation:
            sorter_input += [atom]*coeff
        next_power_of_2 = 2**ceil(log2(len(sorter_input)))
        sorter_input += [false]*(next_power_of_2 - len(sorter_input))
        return self.odd_even_mergesort(sorter_input)

class Linear(object):
    """
    A (canonicalized) linear constraint

    Canonicalized means all coefficients are positive.
    """
    def __init__(self, equation, rhs, total=None, sort=True):
        """
        Equation should be a list of tuples of the form (coeff, atom) (they must
        be tuples so that the resulting object can be hashed). rhs is the
        number on the right-hand side, or a list [lo, hi].

        """
        self.equation = equation
        if sort:
            self.equation = sorted(equation)
        self.equation = tuple(self.equation)
        self.rhs = rhs
        if isinstance(rhs, int):
            self.lo = self.hi = rhs
        else:
            self.lo, self.hi = rhs
        self.total = total or sum([i for i, _ in equation])
        if equation:
            self.LC = self.equation[-1][0]
            self.LA = self.equation[-1][1]
        # self.lower_limit = self.lo - self.total
        # self.upper_limit = self.hi - self.total

    @property
    def coeffs(self):
        if hasattr(self, '_coeffs'):
            return self._coeffs
        self._coeffs = []
        self._atoms = []
        for coeff, atom in self.equation:
            self._coeffs.append(coeff)
            self._atoms.append(atom)
        return self._coeffs

    @property
    def atoms(self):
        if hasattr(self, '_atoms'):
            return self._atoms
        self._coeffs = []
        self._atoms = []
        for coeff, atom in self.equation:
            self._coeffs.append(coeff)
            self._atoms.append(atom)
        return self._atoms

    @property
    def atom2coeff(self):
        return defaultdict(int, {atom: coeff for coeff, atom in self.equation})

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
        if key == slice(None, -1, None):
            total = self.total - self.LC
            sort = False
        else:
            total = None
            sort = True
        return self.__class__(self.equation.__getitem__(key), self.rhs,
            total=total, sort=sort)

    def __eq__(self, other):
        if not isinstance(other, Linear):
            return False
        return (self.equation == other.equation and self.lo == other.lo and
        self.hi == other.hi)

    def __hash__(self):
        try:
            return self._hash
        except AttributeError:
            self._hash = hash((self.equation, self.lo, self.hi))
            return self._hash

    def __str__(self):
        return "Linear(%r, %r)" % (self.equation, self.rhs)

    __repr__ = __str__

def evaluate_eq(eq, sol):
    """
    Evaluate an equation at a solution
    """
    atom2coeff = defaultdict(int, {atom: coeff for coeff, atom in eq})
    t = 0
    for s in sol:
        t += atom2coeff[s]
    return t

def generate_constraints(eq, m, rhs, alg='BDD', sorter_cache={}):
    l = Linear(eq, rhs)
    if not l:
        return set()
    C = Clauses(m)
    additional_clauses = set()
    if alg == 'BDD':
        additional_clauses.add((C.build_BDD(l, polarity=True),))
    elif alg == 'BDD_recursive':
        additional_clauses.add((C.build_BDD_recursive(l, polarity=True),))
    elif alg == 'sorter':
        if l.equation in sorter_cache:
            m, C = sorter_cache[l.equation]
        else:
            if sorter_cache:
                sorter_cache.popitem()
            m = C.build_sorter(l)
            sorter_cache[l.equation] = m, C

        if l.rhs[0]:
            # Output must be between lower bound and upper bound, meaning
            # the lower bound of the sorted output must be true and one more
            # than the upper bound should be false.
            additional_clauses.add((m[l.rhs[0]-1],))
            additional_clauses.add((-m[l.rhs[1]],))
        else:
            # The lower bound is zero, which is always true.
            additional_clauses.add((-m[l.rhs[1]],))
    else:
        raise ValueError("alg must be one of 'BDD', 'BDD_recursive', or 'sorter'")

    return C.clauses | additional_clauses

try:
    pycosat.itersolve({(1,)})
    pycosat_prep = False
except TypeError:
    pycosat_prep = True

def sat(clauses, iterator=False):
    """
    Calculate a SAT solution for `clauses`.

    Returned is the list of those solutions.  When the clauses are
    unsatisfiable, an empty list is returned.

    """
    if pycosat_prep:
        clauses = list(map(list,clauses))
    if iterator:
        return pycosat.itersolve(clauses)
    solution = pycosat.solve(clauses)
    if solution == "UNSAT" or solution == "UNKNOWN": 
        return None
    return solution

def optimize(objective, clauses, bestsol, minval=0, increment=10, alg='BDD', trymin=True):
    """
    Bisect the solution space of a constraint, to minimize it.

    func should be a function that is called with the arguments func(lo_rhs,
    hi_rhs) and returns a list of constraints.

    The midpoint of the bisection will not be more than lo_value + increment.
    To not use it, set a very large increment. The increment argument should
    be used if you expect the optimal solution to be near 0.

    If evalaute_func is given, it is used to evaluate solutions to aid in the bisection.

    """
    if not objective:
        log.debug('Empty objective, trivial solution')
        return clauses, bestsol
    log.debug("Using alg %s" % alg)
    m = len(bestsol)
    bestcon = clauses
    bestval = evaluate_eq(objective, bestsol)
    log.debug("Initial upper bound: %s" % bestsol)
    lo = minval
    # If bestval = lo, we have a minimal solution, but we
    # still need to run the loop at least once to generate
    # the constraints to lock the solution in place.
    hi = max([bestval, lo+1])
    while lo < hi:
        mid = lo if (trymin or lo == bestval) else min([lo + increment, (lo + hi)//2])
        rhs = [lo, mid]
        trymin = False
        if mid == 0:
            constraints = set((-q[1],) for q in objective)
        else:
            constraints = set(generate_constraints(objective, m, [0, mid], alg=alg))
            assert false not in constraints, 'Optimization error'
            if true in constraints:
                constraints = set([])
        newcon = clauses | constraints
        newsol = sat(newcon)
        if newsol is None:
            log.debug("Bisection range %s: failure" % rhs)
            lo = mid+1
        else:
            bestcon = newcon
            bestsol = newsol
            if trymin:
                log.debug("Minimum objective %d satisfiable" % lo)
                break
            hi = evaluate_eq(objective, newsol)
            log.debug("Bisection range %s: success, value %s" % (rhs,hi))
    return bestcon, bestsol

class MaximumIterationsError(Exception):
    pass

def minimal_unsatisfiable_subset(clauses, sat=sat, log=False):
    """
    Given a set of clauses, find a minimal unsatisfiable subset (an
    unsatisfiable core)

    A set is a minimal unsatisfiable subset if no proper subset is
    unsatisfiable.  A set of clauses may have many minimal unsatisfiable
    subsets of different sizes.

    If log=True, progress bars will be displayed with the progress.

    sat should be a function that takes a tuple of clauses and returns True if
    the clauses are satisfiable and False if they are not.  The algorithm will
    work with any order-reversing function (reversing the order of subset and
    the order False < True), that is, any function where (A <= B) iff (sat(B)
    <= sat(A)), where A <= B means A is a subset of B and False < True).

    Algorithm
    =========

    Algorithm suggested from
    http://www.slideshare.net/pvcpvc9/lecture17-31382688. We do a binary
    search on the clauses by splitting them in halves A and B. If A or B is
    UNSAT, we use that and repeat. Otherwise, we recursively check A, but each
    time we do a sat query, we include B, until we have a minimal subset A* of
    A such that A* U B is UNSAT. Then we find a minimal subset B* of B such
    that A* U B* is UNSAT. Then A* U B* will be a minimal unsatisfiable subset
    of the original set of clauses.

    Proof: If some proper subset C of A* U B* is UNSAT, then there is some
    clause c in A* U B* not in C. If c is in A*, then that means (A* - {c}) U
    B* is UNSAT, and hence (A* - {c}) U B is UNSAT, since it is a superset,
    which contradicts A* being the minimal subset of A with such
    property. Similarly, if c is in B, then A* U (B* - {c}) is UNSAT, but B* -
    {c} is a strict subset of B*, contradicting B* being the minimal subset of
    B with this property.

    """
    if log:
        from conda.console import setup_verbose_handlers
        setup_verbose_handlers()
        start = lambda x: logging.getLogger('progress.start').info(x)
        update = lambda x, y: logging.getLogger('progress.update').info(("%s/%s" % (x, y), x))
        stop = lambda: logging.getLogger('progress.stop').info(None)
    else:
        start = lambda x: None
        update = lambda x, y: None
        stop = lambda: None

    clauses = tuple(clauses)
    if sat(clauses):
        raise ValueError("Clauses are not unsatisfiable")

    def split(S):
        """
        Split S into two equal parts
        """
        S = tuple(S)
        L = len(S)
        return S[:L//2], S[L//2:]

    def minimal_unsat(clauses, include=()):
        """
        Return a minimal subset A of clauses such that A + include is
        unsatisfiable.

        Implicitly assumes that clauses + include is unsatisfiable.
        """
        global L, d

        # assert not sat(clauses + include), (len(clauses), len(include))

        # Base case: Since clauses + include is implicitly assumed to be
        # unsatisfiable, if clauses has only one element, it must be its own
        # minimal subset
        if len(clauses) == 1:
            return clauses

        A, B = split(clauses)

        # If one half is unsatisfiable (with include), we can discard the
        # other half.

        # To display progress, every time we discard clauses, we update the
        # progress by that much.
        if not sat(A + include):
            d += len(B)
            update(d, L)
            return minimal_unsat(A, include)
        if not sat(B + include):
            d += len(A)
            update(d, L)
            return minimal_unsat(B, include)

        Astar = minimal_unsat(A, B + include)
        Bstar = minimal_unsat(B, Astar + include)
        return Astar + Bstar

    global L, d
    L = len(clauses)
    d = 0
    start(L)
    ret = minimal_unsat(clauses)
    stop()
    return ret
