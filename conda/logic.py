# -*- coding: utf-8 -*-
"""
The basic idea to nest logical expressions is instead of trying to denest
things via distribution, we add new variables. So if we have some logical
expression expr, we replace it with x and add expr <-> x to the clauses,
where x is a new variable, and expr <-> x is recursively evaluated in the
same way, so that the final clauses are ORs of atoms.

To use this, create a new Clauses object with the max var, for instance, if you
already have [[1, 2, -3]], you would use C = Clause(3).  All functions return
a new literal, which represents that function, or True or False if the expression
can be resolved fully. They may also add new clauses to C.clauses, which
will then be delivered to the SAT solver.

All functions take atoms as arguments (an atom is an integer, representing a
literal or a negated literal, or boolean constants True or False; that is,
it is the callers' responsibility to do the conversion of expressions
recursively. This is done because we do not have data structures
representing the various logical classes, only atoms.

The polarity argument can be set to True or False if you know that the literal
being used will only be used in the positive or the negative, respectively
(e.g., you will only use x, not -x).  This will generate fewer clauses. It
is probably best if you do not take advantage of this directly, but rather
through the Require and Prevent functions.

"""
from functools import total_ordering
from itertools import chain, combinations
from conda.compat import iteritems, string_types
import logging
import pycosat

dotlog = logging.getLogger('dotupdate')
log = logging.getLogger(__name__)


# Code that uses special cases (generates no clauses) is in ADTs/FEnv.h in
# minisatp. Code that generates clauses is in Hardware_clausify.cc (and are
# also described in the paper, "Translating Pseudo-Boolean Constraints into
# SAT," Eén and Sörensson).
class Clauses(object):
    def __init__(self, m=0):
        self.clauses = []
        self.names = {}
        self.indices = {}
        self.fixed = {}
        self.last_prune = 0
        self.m = m
        self.stack = []

    def name_var(self, m, name):
        nname = '!' + name
        self.names[name] = m
        self.names[nname] = -m
        if type(m) is not bool and m not in self.indices:
            self.indices[m] = name
            self.indices[-m] = nname
        return m

    def new_var(self, name=None):
        m = self.m + 1
        self.m = m
        if name:
            self.name_var(m, name)
        return m

    def from_name(self, name):
        return self.names.get(name)

    def from_index(self, m):
        return self.indices.get(m)

    def varnum(self, x):
        return self.names[x] if isinstance(x, string_types) else x

    def ITE_(self, c, t, f, polarity):
        if c is True:
            return t
        if c is False:
            return f
        if t is True or t is c:
            return self.Or_(c, f, polarity)
        if t is False or t is -c:
            return self.And_(-c, f, polarity)
        if f is False or f is c:
            return self.And_(c, t, polarity)
        if f is True or f is -c:
            return self.Or_(t, -c, polarity)
        if t is f:
            return t
        if t is -f:
            return self.Xor_(c, f, polarity)
        x = self.new_var()
        # Basically, c ? t : f is equivalent to (c AND t) OR (NOT c AND f)
        # The third clause in each group is redundant but assists the unit
        # propagation in the SAT solver.
        if polarity in {False, None}:
            self.clauses.extend(((-c, -t, x), (c, -f, x), (-t, -f, x)))
        if polarity in {True, None}:
            self.clauses.extend(((-c, t, -x), (c, f, -x), (t, f, -x)))
        return x

    def ITE(self, c, t, f, polarity=None, name=None):
        """
        if c then t else f

        In this function, if any of c, t, or f are True and False the resulting
        expression is resolved.
        """
        c = self.varnum(c)
        t = self.varnum(t)
        f = self.varnum(f)
        x = self.ITE_(c, t, f, polarity)
        return self.name_var(x, name) if name else x

    def Enforce(self, direction, what, *args, **kwargs):
        nz = len(self.clauses)
        kwargs.setdefault('polarity', direction)
        name = kwargs.get('name')
        if name:
            del kwargs['name']
        x = what.__get__(self, Clauses)(*args, **kwargs)
        if type(x) is bool:
            self.clauses = self.clauses[:nz]
            x = (x == direction)
            if x is False:
                self.clauses.extend(((1,), (-1,)))
        else:
            if not direction:
                x = -x
            self.clauses.append((x,))
        return self.name_var(x, name) if name else x

    def Prevent(self, what, *args, **kwargs):
        assert kwargs.get('polarity') is not True
        return self.Enforce(False, what, *args, **kwargs)

    def Require(self, what, *args, **kwargs):
        assert kwargs.get('polarity') is not False
        return self.Enforce(True, what, *args, **kwargs)

    def Invert(self, what, *args, **kwargs):
        pol = kwargs.get('polarity')
        if pol:
            kwargs['polarity'] = not pol
        return self.Not(what.__get__(self, Clauses)(*args, **kwargs))

    def Not(self, x, polarity=None):
        if type(x) is bool:
            return not x
        if isinstance(x, string_types):
            return x[1:] if x[0] == '!' else '!' + x
        return -x

    def And_(self, f, g, polarity):
        if f is False or g is False:
            return False
        if f is True:
            return g
        if g is True:
            return f
        if f is g:
            return f
        if f is -g:
            return False
        x = self.new_var()
        if polarity is True:
            self.clauses.extend(((-x, f), (-x, g)))
        elif polarity is False:
            self.clauses.append((x, -f, -g))
        else:
            self.clauses.extend(((-x, f), (-x, g), (x, -f, -g)))
        return x

    def And(self, f, g, polarity=None, name=None):
        f = self.varnum(f)
        g = self.varnum(g)
        x = self.And_(f, g, polarity)
        return self.name_var(x, name) if name else x

    def All(self, iter, polarity=None, name=None):
        vals = set()
        x = None
        for v in iter:
            v = self.varnum(v)
            if v is False:
                x = False
                break
            if v is True:
                continue
            if -v in vals:
                x = False
                break
            vals.add(v)
        if x is None:
            nv = len(vals)
            if nv == 0:
                x = True
            elif nv == 1:
                x = next(v for v in vals)
        if x is None:
            x = self.new_var()
            if polarity in {True, None}:
                self.clauses.extend((-x, v) for v in vals)
            if polarity in {False, None}:
                self.clauses.append((x,) + tuple(-v for v in vals))
        return self.name_var(x, name) if name else x

    def Or_(self, f, g, polarity):
        if f is True or g is True:
            return True
        if f is False:
            return g
        if g is False:
            return f
        if f is g:
            return f
        if f is -g:
            return True
        x = self.new_var()
        if polarity is True:
            self.clauses.append((-x, f, g))
        elif polarity is False:
            self.clauses.extend(((x, -f), (x, -g)))
        else:
            self.clauses.extend(((x, -f), (x, -g), (-x, f, g)))
        return x

    def Or(self, f, g, polarity=None, name=None):
        f = self.varnum(f)
        g = self.varnum(g)
        x = self.Or_(f, g, polarity)
        return self.name_var(x, name) if name else x

    def Any(self, iter, polarity=None, name=None):
        vals = set()
        x = None
        for v in iter:
            v = self.varnum(v)
            if v is True:
                x = True
                break
            if v is False:
                continue
            if -v in vals:
                x = True
                break
            vals.add(v)
        if x is None:
            nv = len(vals)
            if nv == 0:
                x = False
            elif nv == 1:
                x = next(v for v in vals)
        if x is None:
            x = self.new_var()
            if polarity in {True, None}:
                self.clauses.append((-x,) + tuple(vals))
            if polarity in {False, None}:
                self.clauses.extend((x, -f) for f in vals)
        return self.name_var(x, name) if name else x

    def Xor_(self, f, g, polarity):
        if f is False:
            return g
        if f is True:
            return self.Not(g)
        if g is False:
            return f
        if g is True:
            return -f
        if f is g:
            return False
        if f is -g:
            return True
        x = self.new_var()
        if polarity is True:
            self.clauses.extend(((-x, f, g), (-x, -f, -g)))
        elif polarity is False:
            self.clauses.extend(((x, -f, g), (x, f, -g)))
        else:
            self.clauses.extend(((-x, f, g), (-x, -f, -g), (x, -f, g), (x, f, -g)))
        return x

    def Xor(self, f, g, polarity=None, name=None):
        f = self.varnum(f)
        g = self.varnum(g)
        x = self.Xor_(f, g, polarity)
        return self.name_var(x, name) if name else x

    def AtMostOne_1(self, vals, polarity=None, name=None):
        combos = []
        for v1, v2 in combinations(map(self.Not, map(self.varnum, vals)), 2):
            combos.append(self.Or(v1, v2, polarity))
        return self.All(combos, polarity=polarity, name=name)

    def AtMostOne_2(self, vals, polarity=None, name=None):
        return self.LinearBound([(1, self.varnum(k)) for k in vals],
                                0, 1, polarity=polarity, name=name)

    def AtMostOne(self, vals, BDD=None, polarity=None, name=None):
        vals = list(vals)
        nv = len(vals)
        if BDD is False or nv < 5 - (polarity is not True):
            return self.AtMostOne_1(vals, polarity, name)
        else:
            return self.AtMostOne_2(vals, polarity, name)

    def ExactlyOne_1(self, vals, polarity=None, name=None):
        r1 = self.AtMostOne_1(vals, polarity=polarity)
        r2 = self.Any(vals, polarity=polarity)
        return self.And(r1, r2, polarity=polarity, name=name)

    def ExactlyOne_2(self, vals, polarity=None, name=None):
        return self.LinearBound([(1, self.varnum(k)) for k in vals],
                                1, 1, polarity=polarity, name=name)

    def ExactlyOne(self, vals, BDD=None, polarity=None, name=None):
        vals = list(vals)
        nv = len(vals)
        if BDD is False or nv < 2:
            return self.ExactlyOne_1(vals, polarity, name)
        else:
            return self.ExactlyOne_2(vals, polarity, name)

    def LinearBound(self, equation, lo, hi, polarity=None, name=None):
        nz = len(self.clauses)
        if type(equation) is dict:
            equation = [(c, self.varnum(a)) for a, c in iteritems(equation)]
        if any(type(a) is bool or a in self.fixed for c, a in equation):
            olen = len(equation)
            offset = sum(c * (1 if a is True else self.fixed[a])
                         for c, a in equation if a is True or a in self.fixed)
            equation = ((c, a) for c, a in equation
                        if type(a) is not bool and a not in self.fixed)
            log.debug('Eliminating %d fixed terms' % (len(equation)-olen))
        if any(c <= 0 for c, a in equation):
            # Remove resolved terms and convert negative coefficients
            # l <= c1 True + c2 False + S <= u
            #    ---> l - c1 <= S <= u - c1
            # l <= c x + S <= u, c < 0
            #    ---> l <= c - c !x + S <= u
            #    ---> l - c <= -c !x + S <= u
            offset = sum(c for c, a in equation if c < 0)
            equation = [(c, a) if c > 0 else (-c, -a) for c, a in equation if c]
            log.debug('Correcting negative terms')
            lo -= offset
            hi -= offset
        if any(c > hi for c, a in equation):
            # Prune coefficients that must be zero
            olen = len(equation)
            pvals = [-a for c, a in equation if c > hi]
            prune = self.All(pvals, polarity=polarity)
            equation = [(c, a) for c, a in equation if c <= hi]
            log.debug('Eliminating %d/%d terms for bound violation' %
                      (olen-len(equation), olen))
        else:
            prune = True
        # Tighten bounds
        lo = max([lo, 0])
        hi = min([hi, sum(c for c, a in equation)])
        if lo > hi:
            res = False
        elif not equation:
            res = True if lo == 0 else False
        else:
            # The equation is sorted in order of increasing coefficients.
            # Then we take advantage of the following recurrence:
            #                l      <= S + cN xN <= u
            #  => IF xN THEN l - cN <= S         <= u - cN
            #           ELSE l      <= S         <= u
            # we use memoization to prune common subexpressions
            equation = sorted(equation)
            total = sum(i for i, _ in equation)
            first_stack = (len(equation)-1, 0, total)
            call_stack = [first_stack]
            ret = {}
            csum = 0
            while call_stack:
                ndx, csum, total = call_stack[-1]
                lower_limit = lo - csum
                upper_limit = hi - csum
                if lower_limit <= 0 and upper_limit >= total:
                    ret[call_stack.pop()] = True
                    continue
                if lower_limit > total or upper_limit < 0:
                    ret[call_stack.pop()] = False
                    continue
                LC, LA = equation[ndx]
                ndx -= 1
                total -= LC
                hi_key = (ndx, csum if LA < 0 else csum + LC, total)
                thi = ret.get(hi_key)
                if thi is None:
                    call_stack.append(hi_key)
                    continue
                lo_key = (ndx, csum + LC if LA < 0 else csum, total)
                tlo = ret.get(lo_key)
                if tlo is None:
                    call_stack.append(lo_key)
                    continue
                ret[call_stack.pop()] = self.ITE_(abs(LA), thi, tlo, polarity)
            res = ret[first_stack]
        res = self.And(prune, res, polarity=polarity)
        if res is True or res is False:
            self.clauses = self.clauses[:nz]
        return self.name_var(res, name) if name else res

    def sat(self, additional=None, includeIf=False, names=False):
        """
        Calculate a SAT solution for the current clause set.

        Returned is the list of those solutions.  When the clauses are
        unsatisfiable, an empty list is returned.

        """
        if additional:
            additional = list(map(lambda x: tuple(map(self.varnum, x)), additional))
            clauses = chain(self.clauses, additional)
        else:
            clauses = self.clauses
        solution = pycosat.solve(clauses)
        if solution == "UNSAT" or solution == "UNKNOWN":
            return None
        if additional and includeIf:
            self.clauses.extend(additional)
        if len(solution) < self.m:
            solution = {abs(s): s for s in solution}
            solution = [solution.get(s, s) for s in range(1, self.m+1)]
        if names:
            return set(nm for nm in (self.indices.get(s) for s in solution) if nm and nm[0] != '!')
        return solution

    def itersolve(self, constraints=None, m=None):
        if constraints is None:
            constraints = []
        exclude = []
        if m is None:
            m = self.m
        while True:
            # We don't use pycosat.itersolve because it is more
            # important to limit the number of terms added to the
            # exclusion list, in our experience. Once we update
            # pycosat to do this, this can use it.
            sol = self.sat(chain(constraints, exclude))
            if sol is None:
                return
            yield sol
            exclude.append([-k for k in sol if -m <= k <= m])

    def minimize(self, objective, bestsol, minval=None, increment=10):
        """
        Bisect the solution space of a constraint, to minimize it.

        func should be a function that is called with the arguments func(lo_rhs,
        hi_rhs) and returns a list of constraints.

        The midpoint of the bisection will not be more than lo_value + increment.
        To not use it, set a very large increment. The increment argument should
        be used if you expect the optimal solution to be near 0.

        """
        if not objective:
            log.debug('Empty objective, trivial solution')
            return bestsol, 0

        if type(objective) is dict:
            odict = {self.varnum(k): v for k, v in iteritems(objective)}
            objective = [(v, k) for k, v in iteritems(odict)]
        else:
            odict = {self.varnum(atom): coeff for coeff, atom in objective}

        bestm = self.m
        bestcon = []
        bestval = evaluate_eq(odict, bestsol)
        log.debug('Initial objective: %d' % bestval)

        # If we got lucky and the initial solution is optimal, we still
        # need to generate the constraints at least once
        try0 = lo = min([bestval, max([0, minval]) if minval else 0])
        hi = bestval

        log.debug("Initial range (%d,%d,%d)" % (lo, bestval, hi))
        while True:
            if try0 is None:
                mid = min([lo + increment, (lo+hi)//2])
            else:
                mid = try0
                try0 = None
            C2 = Clauses(self.m)
            C2.Require(C2.LinearBound, objective, lo, mid)
            log.debug('Bisection range: (%d,%d), (%d+%d) clauses' %
                      (lo, mid, len(self.clauses), len(C2.clauses)))
            newsol = self.sat(C2.clauses)
            if newsol is None:
                log.debug("Bisection failure")
                lo = mid + 1
            else:
                bestm = C2.m
                bestcon = C2.clauses
                bestsol = newsol
                bestval = evaluate_eq(odict, newsol)
                hi = mid
                log.debug("Bisection success, new best=(%d,%d,%d)" % (lo, mid, bestval))
                if lo == hi:
                    break

        # lfixed = len(self.fixed)
        self.clauses.extend(bestcon)
        self.m = bestm

        # nnew = 0
        # for c in self.clauses[self.last_prune:]:
        #     if len(c) == 1:
        #         self.fixed[c[0]] = 1
        #         self.fixed[-c[0]] = 0
        #         nnew += 1
        # self.last_prune = len(self.clauses)
        # for c, a in objective:
        #     if c > bestval and a not in self.fixed:
        #         self.fixed[a] = 0
        #         self.fixed[-a] = 1
        #         self.clauses.append((-a,))
        #         nnew += 1
        # if nnew:
        #     log.debug('Fixing %d variables' % nnew)

        # if lfixed < len(self.fixed):
        #     clauses2 = []
        #     f = self.fixed
        #     nnew = nold = 0
        #     for clause in self.clauses:
        #         if len(clause) == 1:
        #             clauses2.append(clause)
        #             continue
        #         nold += 1
        #         if len(clause) > 1 and any(cc in f for cc in clause):
        #             if any(f.get(cc, 0) == 1 for cc in clause):
        #                 cdrop = tuple(cc for cc in clause if f.get(cc, 0) == 1)
        #                 continue
        #             oclause = clause
        #             clause = tuple(cc for cc in clause if cc not in f)
        #             if len(clause) == 1:
        #                 f[clause[0]] = 1
        #                 f[-clause[0]] = 0
        #             else:
        #                 nnew += 1
        #         clauses2.append(clause)
        #     log.debug('Reducing non-trivial clauses from %d -> %d' % (nold, nnew))
        #     self.last_prune = len(clauses2)
        #     self.clauses = clauses2

        return bestsol, bestval


def evaluate_eq(eq, sol):
    if type(eq) is not dict:
        eq = {c: v for v, c in eq if type(c) is not bool}
    return sum(eq.get(s, 0) for s in sol if type(s) is not bool)


def minimal_unsatisfiable_subset(clauses, sat, log=False):
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
        start = lambda x: None  # noqa
        update = lambda x, y: None  # noqa
        stop = lambda: None  # noqa

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
