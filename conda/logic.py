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
from itertools import chain
import logging
import pycosat

dotlog = logging.getLogger('dotupdate')
log = logging.getLogger(__name__)

# Custom classes for true and false. Using True and False is too risky, since
# True == 1, so it might be confused for the literal 1.
class TrueClass(object):
    def __eq__(self, other):
        return other is true
    def __neg__(self):
        return false
    def __str__(self):
        return "true"
    __repr__ = __str__
true = TrueClass()

class FalseClass(object):
    def __eq__(self, other):
        return other is false
    def __neg__(self):
        return true
    def __str__(self):
        return "false"
    __repr__ = __str__
false = FalseClass()

# Code that uses special cases (generates no clauses) is in ADTs/FEnv.h in
# minisatp. Code that generates clauses is in Hardware_clausify.cc (and are
# also described in the paper, "Translating Pseudo-Boolean Constraints into
# SAT," Eén and Sörensson).

class Clauses(object):
    def __init__(self, MAX_N=0):
        self.clauses = []
        self.MAX_N = MAX_N

    def get_new_var(self):
        self.MAX_N += 1
        return self.MAX_N

    def ITE(self, c, t, f, polarity=None):
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
            self.clauses.extend((
                # Negative
                (-c, -t, x),
                (c, -f, x),
                (-t, -f, x), # Red
                ))
        if polarity in {True, None}:
            self.clauses.extend((
                # Positive
                (-c, t, -x),
                (c, f, -x),
                (t, f, -x), # Red
                ))

        return x

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
            self.clauses.extend((
                # positive
                # ~f -> ~x, ~g -> ~x
                (-x, f),
                (-x, g),
                ))
        if polarity in {False, None}:
            self.clauses.append(
            # negative
            # (f AND g) -> x
            (x, -f, -g),
            )

        return x

    def Or(self, f, g, polarity=None):
        if polarity is not None:
            polarity = not polarity
        return -self.And(-f, -g, polarity=polarity)

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
            self.clauses.extend((
                # Positive
                (-x, f, g),
                (-x, -f, -g),
            ))
        if polarity in {False, None}:
            self.clauses.extend((
                # Negative
                (x, -f, g),
                (x, f, -g),
            ))
        return x

    def build_BDD(self, equation, lo, hi, polarity=None):
        equation = sorted(equation)
        total = sum(i for i,_ in equation)
        first_stack = (len(equation)-1,0,total)
        call_stack = [first_stack]
        ret = {}
        csum = 0
        while call_stack:
            ndx, csum, total = call_stack[-1]
            lower_limit = lo - csum
            upper_limit = hi - csum
            if lower_limit <= 0 and upper_limit >= total:
                ret[call_stack.pop()] = true
                continue
            if lower_limit > total or upper_limit < 0:
                ret[call_stack.pop()] = false
                continue
            LC, LA = equation[ndx]
            ndx -= 1
            total -= LC
            hi_key = (ndx,csum if LA < 0 else csum + LC,total)
            thi = ret.get(hi_key)
            if thi is None:
                call_stack.append(hi_key)
                continue
            lo_key = (ndx,csum + LC if LA < 0 else csum,total)
            tlo = ret.get(lo_key)
            if tlo is None:
                call_stack.append(lo_key)
                continue
            ret[call_stack.pop()] = self.ITE(abs(LA), thi, tlo, polarity=polarity)
        return ret[first_stack]

def evaluate_eq(eq, sol):
    """
    Evaluate an equation at a solution
    """
    atom2coeff = defaultdict(int, {atom: coeff for coeff, atom in eq})
    t = 0
    for s in sol:
        t += atom2coeff[s]
    return t

def generate_constraints(eq, m, rhs):
    # If a coefficient is larger than rhs then we know it has to be
    # set to zero. That's a lot quicker than building it into the adder
    ub = rhs[-1]
    C = Clauses(m)
    C.clauses.extend((-a,) for c,a in eq if c>ub)
    nz = len(C.clauses)
    if nz < len(eq):
        eq = [q for q in eq if q[0]<=rhs[1]]
        C.clauses.append((C.build_BDD(eq, rhs[0], rhs[1], polarity=True),))
    assert false not in C.clauses, 'Optimization error'
    return [] if true in C.clauses else C.clauses

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

def optimize(objective, clauses, bestsol, minval=0, increment=10, trymin=True, trymax=False):
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
    m = len(bestsol)
    bestcon = []
    bestval = evaluate_eq(objective, bestsol)
    log.debug("Initial upper bound: %s" % bestval)
    lo = minval
    # If bestval = lo, we have a minimal solution, but we
    # still need to run the loop at least once to generate
    # the constraints to lock the solution in place.
    hi = max([bestval, lo+1])
    while lo < hi:
        if lo == bestval or trymin and not trymax:
            mid = lo
        elif trymax:
            mid = hi - 1
        else:
            mid = min([lo + increment, (lo + hi)//2])
        trymin = trymax = False
        # Empirically, using [0,mid] instead of [lo,mid] is slightly faster
        # And since we're minimizing it doesn't matter mathematically
        constraints = generate_constraints(objective, m, [0, mid])
        newsol = sat(chain(clauses,constraints))
        if newsol is None:
            log.debug("Bisection range %s: failure" % (rhs,))
            lo = mid+1
        else:
            bestcon = constraints
            bestsol = newsol
            if trymin:
                log.debug("Minimum objective %d satisfiable" % lo)
                break
            hi = evaluate_eq(objective, newsol)
            log.debug("Bisection range %s: success, value %s" % (rhs,hi))
    return clauses + bestcon, bestsol

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
