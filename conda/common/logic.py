# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
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
from __future__ import absolute_import, division, print_function, unicode_literals

from array import array
from itertools import chain, combinations
from logging import DEBUG, getLogger

from .compat import iteritems

log = getLogger(__name__)


class ClauseList(object):
    """Storage for the CNF clauses, represented as a list of tuples of ints."""
    def __init__(self):
        self._clause_list = []
        # Methods append and extend are directly bound for performance reasons,
        # to avoid call overhead and lookups.
        self.append = self._clause_list.append
        self.extend = self._clause_list.extend

    def get_clause_count(self):
        """
        Return number of stored clauses.
        """
        return len(self._clause_list)

    def save_state(self):
        """
        Get state information to be able to revert temporary additions of
        supplementary clauses.  ClauseList: state is simply the number of clauses.
        """
        return len(self._clause_list)

    def restore_state(self, saved_state):
        """
        Restore state saved via `save_state`.
        Removes clauses that were added after the sate has been saved.
        """
        len_clauses = saved_state
        self._clause_list[len_clauses:] = []

    def as_list(self):
        """Return clauses as a list of tuples of ints."""
        return self._clause_list

    def as_array(self):
        """
        Return clauses as a flat int array, each clause being terminated by 0.
        """
        clause_array = array('i')
        for c in self._clause_list:
            clause_array.extend(c)
            clause_array.append(0)
        return clause_array


class ClauseArray(object):
    """
    Storage for the CNF clauses, represented as a flat int array.
    Each clause is terminated by int(0).
    """
    def __init__(self):
        self._clause_array = array('i')
        # Methods append and extend are directly bound for performance reasons,
        # to avoid call overhead and lookups.
        self._array_append = self._clause_array.append
        self._array_extend = self._clause_array.extend

    def extend(self, clauses):
        for clause in clauses:
            self.append(clause)

    def append(self, clause):
        self._array_extend(clause)
        self._array_append(0)

    def get_clause_count(self):
        """
        Return number of stored clauses.
        This is an O(n) operation since we don't store the number of clauses
        explicitly due to performance reasons (Python interpreter overhead in
        self.append).
        """
        return self._clause_array.count(0)

    def save_state(self):
        """
        Get state information to be able to revert temporary additions of
        supplementary clauses. ClauseArray: state is the length of the int
        array, NOT number of clauses.
        """
        return len(self._clause_array)

    def restore_state(self, saved_state):
        """
        Restore state saved via `save_state`.
        Removes clauses that were added after the sate has been saved.
        """
        len_clause_array = saved_state
        self._clause_array[len_clause_array:] = array('i')

    def as_list(self):
        """Return clauses as a list of tuples of ints."""
        clause = []
        for v in self._clause_array:
            if v == 0:
                yield tuple(clause)
                clause.clear()
            else:
                clause.append(v)

    def as_array(self):
        """
        Return clauses as a flat int array, each clause being terminated by 0.
        """
        return self._clause_array


class SatSolver(object):
    """
    Simple wrapper to call a SAT solver given a ClauseList/ClauseArray instance.
    """

    def __init__(self, **run_kwargs):
        self._run_kwargs = run_kwargs or {}
        self._clauses = ClauseList()
        # Bind some methods of _clauses to reduce lookups and call overhead.
        self.add_clause = self._clauses.append
        self.add_clauses = self._clauses.extend

    def get_clause_count(self):
        return self._clauses.get_clause_count()

    def as_list(self):
        return self._clauses.as_list()

    def save_state(self):
        return self._clauses.save_state()

    def restore_state(self, saved_state):
        return self._clauses.restore_state(saved_state)

    def run(self, m, **kwargs):
        run_kwargs = self._run_kwargs.copy()
        run_kwargs.update(kwargs)
        solver = self.setup(m, **run_kwargs)
        sat_solution = self.invoke(solver)
        solution = self.process_solution(sat_solution)
        return solution

    def setup(self, m, **kwargs):
        """Create a solver instance, add the clauses to it, and return it."""
        raise NotImplementedError()

    def invoke(self, solver):
        """Start the actual SAT solving and return the calculated solution."""
        raise NotImplementedError()

    def process_solution(self, sat_solution):
        """
        Process the solution returned by self.invoke.
        Returns a list of satisfied variables or None if no solution is found.
        """
        raise NotImplementedError()


class PycoSatSolver(SatSolver):
    def setup(self, m, limit=0, **kwargs):
        from pycosat import itersolve

        # NOTE: The iterative solving isn't actually used here, we just call
        #       itersolve to separate setup from the actual run.
        return itersolve(self._clauses.as_list(), vars=m, prop_limit=limit)
        # If we add support for passing the clauses as an integer stream to the
        # solvers, we could also use self._clauses.as_array like this:
        # return itersolve(self._clauses.as_array(), vars=m, prop_limit=limit)

    def invoke(self, iter_sol):
        try:
            sat_solution = next(iter_sol)
        except StopIteration:
            sat_solution = "UNSAT"
        del iter_sol
        return sat_solution

    def process_solution(self, sat_solution):
        if sat_solution in ("UNSAT", "UNKNOWN"):
            return None
        return sat_solution


class CryptoMiniSatSolver(SatSolver):
    def setup(self, m, threads=1, **kwargs):
        from pycryptosat import Solver

        solver = Solver(threads=threads)
        solver.add_clauses(self._clauses.as_list())
        return solver

    def invoke(self, solver):
        sat, sat_solution = solver.solve()
        if not sat:
            sat_solution = None
        return sat_solution

    def process_solution(self, solution):
        if not solution:
            return None
        # The first element of the solution is always None.
        solution = [i for i, b in enumerate(solution) if b]
        return solution


class PySatSolver(SatSolver):
    def setup(self, m, **kwargs):
        from pysat.solvers import Glucose4

        solver = Glucose4()
        solver.append_formula(self._clauses.as_list())
        return solver

    def invoke(self, solver):
        if not solver.solve():
            sat_solution = None
        else:
            sat_solution = solver.get_model()
        solver.delete()
        return sat_solution

    def process_solution(self, sat_solution):
        if sat_solution is None:
            solution = None
        else:
            solution = sat_solution
        return solution


# Code that uses special cases (generates no clauses) is in ADTs/FEnv.h in
# minisatp. Code that generates clauses is in Hardware_clausify.cc (and are
# also described in the paper, "Translating Pseudo-Boolean Constraints into
# SAT," Eén and Sörensson).
class Clauses(object):
    def __init__(self, m=0, sat_solver_cls=PycoSatSolver):
        self.names = {}
        self.indices = {}
        self.unsat = False
        self.m = m
        self._sat_solver = sat_solver_cls()
        # Bind some methods of _sat_solver to reduce lookups and call overhead.
        self.add_clause = self._sat_solver.add_clause
        self.add_clauses = self._sat_solver.add_clauses

    def get_clause_count(self):
        return self._sat_solver.get_clause_count()

    def as_list(self):
        return self._sat_solver.as_list()

    def name_var(self, m, name):
        nname = '!' + name
        self.names[name] = m
        self.names[nname] = -m
        if type(m) is not bool and m not in self.indices:
            self.indices[m] = name
            self.indices[-m] = nname
        return m

    def _new_var(self):
        m = self.m + 1
        self.m = m
        return m

    def new_var(self, name=None):
        m = self._new_var()
        if name:
            self.name_var(m, name)
        return m

    def from_name(self, name):
        return self.names.get(name)

    def from_index(self, m):
        return self.indices.get(m)

    def Assign_(self, vals, name=None):
        x = self._assign_no_name(vals)
        if not name:
            return x
        if isinstance(x, bool):
            x = self._new_var()
            self.add_clause((x,) if vals else (-x,))
        return self.name_var(x, name)

    def _assign_no_name(self, vals):
        if isinstance(vals, tuple):
            x = self._new_var()
            self.add_clauses((-x,) + y for y in vals[0])
            self.add_clauses((x,) + y for y in vals[1])
            return x
        return vals

    def Convert_(self, x):
        tx = type(x)
        if tx in (tuple, list):
            return tx(map(self.Convert_, x))
        return self.names.get(x, x)

    def Eval_(self, func, args, polarity, name, conv=True):
        if conv:
            args = self.Convert_(args)
        saved_state = self._sat_solver.save_state()
        vals = func(*args, polarity=polarity)
        if name is None:
            return self._assign_no_name(vals)
        if name is not False:
            return self.Assign_(vals, name)
        # eval without assignment:
        tvals = type(vals)
        if tvals is tuple:
            self.add_clauses(vals[0])
            self.add_clauses(vals[1])
        elif tvals is not bool:
            self.add_clause((vals if polarity else -vals,))
        else:
            self._sat_solver.restore_state(saved_state)
            self.unsat = self.unsat or polarity != vals
        return None

    def Combine_(self, args, polarity):
        if any(v is False for v in args):
            return False
        args = [v for v in args if v is not True]
        nv = len(args)
        if nv == 0:
            return True
        if nv == 1:
            return args[0]
        if all(type(v) is tuple for v in args):
            return (sum((v[0] for v in args), []), sum((v[1] for v in args), []))
        else:
            return self.All_(map(self.Assign_, args), polarity)

    def Prevent(self, what, *args):
        return what.__get__(self, Clauses)(*args, polarity=False, name=False)

    def Require(self, what, *args):
        return what.__get__(self, Clauses)(*args, polarity=True, name=False)

    def Not_(self, x, polarity=None, add_new_clauses=False):
        return (not x) if type(x) is bool else -x

    def Not(self, x, polarity=None, name=None):
        return self.Eval_(self.Not_, (x,), polarity, name)

    def And_(self, f, g, polarity, add_new_clauses=False):
        if f is False or g is False:
            return False
        if f is True:
            return g
        if g is True:
            return f
        if f == g:
            return f
        if f == -g:
            return False
        if g < f:
            f, g = g, f
        if add_new_clauses:
            # This is equivalent to running self._assign_no_name(pval, nval) on
            # the (pval, nval) tuple we return below. Duplicating the code here
            # is an important performance tweak to avoid the costly generator
            # expressions and tuple additions in self._assign_no_name.
            x = self.new_var()
            if polarity in (True, None):
                self.add_clauses([(-x, f,), (-x, g,)])
            if polarity in (False, None):
                self.add_clauses([(x, -f, -g)])
            return x
        pval = [(f,), (g,)] if polarity in (True, None) else []
        nval = [(-f, -g)] if polarity in (False, None) else []
        return pval, nval

    def And(self, f, g, polarity=None, name=None):
        return self.Eval_(self.And_, (f, g), polarity, name)

    def Or_(self, f, g, polarity, add_new_clauses=False):
        if f is True or g is True:
            return True
        if f is False:
            return g
        if g is False:
            return f
        if f == g:
            return f
        if f == -g:
            return True
        if g < f:
            f, g = g, f
        if add_new_clauses:
            x = self.new_var()
            if polarity in (True, None):
                self.add_clauses([(-x, f, g)])
            if polarity in (False, None):
                self.add_clauses([(x, -f,), (x, -g,)])
            return x
        pval = [(f, g)] if polarity in (True, None) else []
        nval = [(-f,), (-g,)] if polarity in (False, None) else []
        return pval, nval

    def Or(self, f, g, polarity=None, name=None):
        return self.Eval_(self.Or_, (f, g), polarity, name)

    def Xor_(self, f, g, polarity, add_new_clauses=False):
        if f is False:
            return g
        if f is True:
            return self.Not_(g, polarity, add_new_clauses=add_new_clauses)
        if g is False:
            return f
        if g is True:
            return -f
        if f == g:
            return False
        if f == -g:
            return True
        if g < f:
            f, g = g, f
        if add_new_clauses:
            x = self.new_var()
            if polarity in (True, None):
                self.add_clauses([(-x, f, g), (-x, -f, -g)])
            if polarity in (False, None):
                self.add_clauses([(x, -f, g), (x, f, -g)])
            return x
        pval = [(f, g), (-f, -g)] if polarity in (True, None) else []
        nval = [(-f, g), (f, -g)] if polarity in (False, None) else []
        return pval, nval

    def Xor(self, f, g, polarity=None, name=None):
        return self.Eval_(self.Xor_, (f, g), polarity, name)

    def ITE_(self, c, t, f, polarity, add_new_clauses=False):
        if c is True:
            return t
        if c is False:
            return f
        if t is True:
            return self.Or_(c, f, polarity, add_new_clauses=add_new_clauses)
        if t is False:
            return self.And_(-c, f, polarity, add_new_clauses=add_new_clauses)
        if f is False:
            return self.And_(c, t, polarity, add_new_clauses=add_new_clauses)
        if f is True:
            return self.Or_(t, -c, polarity, add_new_clauses=add_new_clauses)
        if t == c:
            return self.Or_(c, f, polarity, add_new_clauses=add_new_clauses)
        if t == -c:
            return self.And_(-c, f, polarity, add_new_clauses=add_new_clauses)
        if f == c:
            return self.And_(c, t, polarity, add_new_clauses=add_new_clauses)
        if f == -c:
            return self.Or_(t, -c, polarity, add_new_clauses=add_new_clauses)
        if t == f:
            return t
        if t == -f:
            return self.Xor_(c, f, polarity, add_new_clauses=add_new_clauses)
        if t < f:
            t, f, c = f, t, -c
        # Basically, c ? t : f is equivalent to (c AND t) OR (NOT c AND f)
        # The third clause in each group is redundant but assists the unit
        # propagation in the SAT solver.
        if add_new_clauses:
            x = self.new_var()
            if polarity in (True, None):
                self.add_clauses([(-x, -c, t), (-x, c, f), (-x, t, f)])
            if polarity in (False, None):
                self.add_clauses([(x, -c, -t), (x, c, -f), (x, -t, -f)])
            return x
        pval = [(-c, t), (c, f), (t, f)] if polarity in (True, None) else []
        nval = [(-c, -t), (c, -f), (-t, -f)] if polarity in (False, None) else []
        return pval, nval

    def ITE(self, c, t, f, polarity=None, name=None):
        """
        if c then t else f

        In this function, if any of c, t, or f are True and False the resulting
        expression is resolved.
        """
        return self.Eval_(self.ITE_, (c, t, f), polarity, name)

    def All_(self, iter, polarity=None):
        vals = set()
        for v in iter:
            if v is True:
                continue
            if v is False or -v in vals:
                return False
            vals.add(v)
        nv = len(vals)
        if nv == 0:
            return True
        elif nv == 1:
            return next(v for v in vals)
        pval = [(v,) for v in vals] if polarity in (True, None) else []
        nval = [tuple(-v for v in vals)] if polarity in (False, None) else []
        return pval, nval

    def All(self, iter, polarity=None, name=None):
        return self.Eval_(self.All_, (iter,), polarity, name)

    def Any_(self, iter, polarity):
        vals = set()
        for v in iter:
            if v is False:
                continue
            elif v is True or -v in vals:
                return True
            vals.add(v)
        nv = len(vals)
        if nv == 0:
            return False
        elif nv == 1:
            return next(v for v in vals)
        pval = [tuple(vals)] if polarity in (True, None) else []
        nval = [(-v,) for v in vals] if polarity in (False, None) else []
        return pval, nval

    def Any(self, vals, polarity=None, name=None):
        return self.Eval_(self.Any_, (list(vals),), polarity, name)

    def AtMostOne_NSQ_(self, vals, polarity):
        combos = []
        for v1, v2 in combinations(map(self.Not_, vals), 2):
            combos.append(self.Or_(v1, v2, polarity))
        return self.Combine_(combos, polarity)

    def AtMostOne_NSQ(self, vals, polarity=None, name=None):
        return self.Eval_(self.AtMostOne_NSQ_, (list(vals),), polarity, name)

    def AtMostOne_BDD_(self, vals, polarity=None, name=None):
        vals = [(1, v) for v in vals]
        return self.LinearBound_(vals, 0, 1, True, polarity)

    def AtMostOne_BDD(self, vals, polarity=None, name=None):
        return self.Eval_(self.AtMostOne_BDD_, (list(vals),), polarity, name)

    def AtMostOne(self, vals, polarity=None, name=None):
        vals = list(vals)
        nv = len(vals)
        if nv < 5 - (polarity is not True):
            what = self.AtMostOne_NSQ
        else:
            what = self.AtMostOne_BDD
        return self.Eval_(what, (vals,), polarity, name)

    def ExactlyOne_NSQ_(self, vals, polarity):
        vals = list(vals)
        v1 = self.AtMostOne_NSQ_(vals, polarity)
        v2 = self.Any_(vals, polarity)
        return self.Combine_((v1, v2), polarity)

    def ExactlyOne_NSQ(self, vals, polarity=None, name=None):
        return self.Eval_(self.ExactlyOne_NSQ_, (list(vals),), polarity, name)

    def ExactlyOne_BDD_(self, vals, polarity):
        vals = [(1, v) for v in vals]
        return self.LinearBound_(vals, 1, 1, True, polarity)

    def ExactlyOne_BDD(self, vals, polarity=None, name=None):
        return self.Eval_(self.ExactlyOne_BDD_, (list(vals),), polarity, name)

    def ExactlyOne(self, vals, polarity=None, name=None):
        vals = list(vals)
        nv = len(vals)
        if nv < 2:
            what = self.ExactlyOne_NSQ
        else:
            what = self.ExactlyOne_BDD
        return self.Eval_(what, (vals,), polarity, name)

    def LB_Preprocess_(self, equation):
        if type(equation) is dict:
            equation = [(c, self.names.get(a, a)) for a, c in iteritems(equation)]
        if any(c <= 0 or type(a) is bool for c, a in equation):
            offset = sum(c for c, a in equation if a is True or a is not False and c <= 0)
            equation = [(c, a) if c > 0 else (-c, -a) for c, a in equation
                        if type(a) is not bool and c]
        else:
            offset = 0
        equation = sorted(equation)
        return equation, offset

    def BDD_(self, equation, nterms, lo, hi, polarity):
        # The equation is sorted in order of increasing coefficients.
        # Then we take advantage of the following recurrence:
        #                l      <= S + cN xN <= u
        #  => IF xN THEN l - cN <= S         <= u - cN
        #           ELSE l      <= S         <= u
        # we use memoization to prune common subexpressions
        total = sum(c for c, _ in equation[:nterms])
        target = (nterms-1, 0, total)
        call_stack = [target]
        ret = {}
        call_stack_append = call_stack.append
        call_stack_pop = call_stack.pop
        ret_get = ret.get
        ITE_ = self.ITE_

        csum = 0
        while call_stack:
            ndx, csum, total = call_stack[-1]
            lower_limit = lo - csum
            upper_limit = hi - csum
            if lower_limit <= 0 and upper_limit >= total:
                ret[call_stack_pop()] = True
                continue
            if lower_limit > total or upper_limit < 0:
                ret[call_stack_pop()] = False
                continue
            LC, LA = equation[ndx]
            ndx -= 1
            total -= LC
            hi_key = (ndx, csum if LA < 0 else csum + LC, total)
            thi = ret_get(hi_key)
            if thi is None:
                call_stack_append(hi_key)
                continue
            lo_key = (ndx, csum + LC if LA < 0 else csum, total)
            tlo = ret_get(lo_key)
            if tlo is None:
                call_stack_append(lo_key)
                continue
            # NOTE: The following ITE_ call is _the_ hotspot of the Python-side
            # computations for the overall minimization run. For performance we
            # avoid calling self._assign_no_name here via add_new_clauses=True.
            # If we want to translate parts of the code to a compiled language,
            # self.BDD_ (+ its downward call stack) is the prime candidate!
            ret[call_stack_pop()] = ITE_(abs(LA), thi, tlo, polarity, add_new_clauses=True)
        return ret[target]

    def LinearBound_(self, equation, lo, hi, preprocess, polarity):
        if preprocess:
            equation, offset = self.LB_Preprocess_(equation)
            lo -= offset
            hi -= offset
        nterms = len(equation)
        if nterms and equation[-1][0] > hi:
            nprune = sum(c > hi for c, a in equation)
            log.trace('Eliminating %d/%d terms for bound violation' % (nprune, nterms))
            nterms -= nprune
        else:
            nprune = 0
        # Tighten bounds
        total = sum(c for c, _ in equation[:nterms])
        if preprocess:
            lo = max([lo, 0])
            hi = min([hi, total])
        if lo > hi:
            return False
        if nterms == 0:
            res = lo == 0
        else:
            res = self.BDD_(equation, nterms, lo, hi, polarity)
        if nprune:
            prune = self.All_([-a for c, a in equation[nterms:]], polarity)
            res = self.Combine_((res, prune), polarity)
        return res

    def LinearBound(self, equation, lo, hi, preprocess=True, polarity=None, name=None):
        return self.Eval_(
            self.LinearBound_, (equation, lo, hi, preprocess), polarity, name, conv=False)

    def _run_sat(self, m, limit=0):
        if log.isEnabledFor(DEBUG):
            log.debug("Invoking SAT with clause count: %s", self.get_clause_count())
        solution = self._sat_solver.run(m, limit=limit)
        return solution

    def sat(self, additional=None, includeIf=False, names=False, limit=0):
        """
        Calculate a SAT solution for the current clause set.

        Returned is the list of those solutions.  When the clauses are
        unsatisfiable, an empty list is returned.

        """
        if self.unsat:
            return None
        if not self.m:
            return set() if names else []
        saved_state = self._sat_solver.save_state()
        if additional:
            def preproc(eqs):
                def preproc_(cc):
                    for c in cc:
                        c = self.names.get(c, c)
                        if c is False:
                            continue
                        yield c
                        if c is True:
                            break
                for cc in eqs:
                    cc = tuple(preproc_(cc))
                    if not cc:
                        yield cc
                        break
                    if cc[-1] is not True:
                        yield cc
            additional = list(preproc(additional))
            if additional:
                if not additional[-1]:
                    return None
                self.add_clauses(additional)
        solution = self._run_sat(self.m, limit=limit)
        if additional and (solution is None or not includeIf):
            self._sat_solver.restore_state(saved_state)
        if solution is None:
            return None
        if names:
            return set(nm for nm in (self.indices.get(s) for s in solution) if nm and nm[0] != '!')
        return solution

    def itersolve(self, constraints=None, m=None):
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

    def minimize(self, objective, bestsol=None, trymax=False):
        """
        Minimize the objective function given either by (coeff, integer)
        tuple pairs, or a dictionary of varname: coeff values. The actual
        minimization is multiobjective: first, we minimize the largest
        active coefficient value, then we minimize the sum.
        """
        if bestsol is None or len(bestsol) < self.m:
            log.debug('Clauses added, recomputing solution')
            bestsol = self.sat()
        if bestsol is None or self.unsat:
            log.debug('Constraints are unsatisfiable')
            return bestsol, sum(abs(c) for c, a in objective) + 1 if objective else 1
        if not objective:
            log.debug('Empty objective, trivial solution')
            return bestsol, 0

        if type(objective) is dict:
            objective = [(v, self.names.get(k, k)) for k, v in iteritems(objective)]

        objective, offset = self.LB_Preprocess_(objective)
        maxval = max(c for c, a in objective)

        def peak_val(sol, odict):
            return max(odict.get(s, 0) for s in sol)

        def sum_val(sol, odict):
            return sum(odict.get(s, 0) for s in sol)

        lo = 0
        try0 = 0
        for peak in ((True, False) if maxval > 1 else (False,)):
            if peak:
                log.trace('Beginning peak minimization')
                objval = peak_val
            else:
                log.trace('Beginning sum minimization')
                objval = sum_val

            odict = {a: c for c, a in objective}
            bestval = objval(bestsol, odict)

            # If we got lucky and the initial solution is optimal, we still
            # need to generate the constraints at least once
            hi = bestval
            m_orig = self.m
            if log.isEnabledFor(DEBUG):
                # This is only used for the log message below.
                nz = self.get_clause_count()
            saved_state = self._sat_solver.save_state()
            if trymax and not peak:
                try0 = hi - 1

            log.trace("Initial range (%d,%d)" % (lo, hi))
            while True:
                if try0 is None:
                    mid = (lo+hi) // 2
                else:
                    mid = try0
                if peak:
                    self.Prevent(self.Any, tuple(a for c, a in objective if c > mid))
                    temp = tuple(a for c, a in objective if lo <= c <= mid)
                    if temp:
                        self.Require(self.Any, temp)
                else:
                    self.Require(self.LinearBound, objective, lo, mid, False)
                if log.isEnabledFor(DEBUG):
                    log.trace('Bisection attempt: (%d,%d), (%d+%d) clauses' %
                              (lo, mid, nz, self.get_clause_count() - nz))
                newsol = self.sat()
                if newsol is None:
                    lo = mid + 1
                    log.trace("Bisection failure, new range=(%d,%d)" % (lo, hi))
                    if lo > hi:
                        break
                    # If this was a failure of the first test after peak minimization,
                    # then it means that the peak minimizer is "tight" and we don't need
                    # any further constraints.
                else:
                    done = lo == mid
                    bestsol = newsol
                    bestval = objval(newsol, odict)
                    hi = bestval
                    log.trace("Bisection success, new range=(%d,%d)" % (lo, hi))
                    if done:
                        break
                self.m = m_orig
                # Since we only ever _add_ clauses and only remove then via
                # restore_state, it's fine to test on equality only.
                if self._sat_solver.save_state() != saved_state:
                    self._sat_solver.restore_state(saved_state)
                self.unsat = False
                try0 = None

            log.debug('Final %s objective: %d' % ('peak' if peak else 'sum', bestval))
            if bestval == 0:
                break
            elif peak:
                # Now that we've minimized the peak value, we can drop any terms
                # with coefficients larger than this. Furthermore, since we know
                # at least one peak will be active, our lower bound for the sum
                # equals the peak.
                objective = [(c, a) for c, a in objective if c <= bestval]
                try0 = sum_val(bestsol, odict)
                lo = bestval
            else:
                log.debug('New peak objective: %d' % peak_val(bestsol, odict))

        return bestsol, bestval


def evaluate_eq(eq, sol):
    if type(eq) is not dict:
        eq = {c: v for v, c in eq if type(c) is not bool}
    return sum(eq.get(s, 0) for s in sol if type(s) is not bool)


def minimal_unsatisfiable_subset(clauses, sat):
    """
    Given a set of clauses, find a minimal unsatisfiable subset (an
    unsatisfiable core)

    A set is a minimal unsatisfiable subset if no proper subset is
    unsatisfiable.  A set of clauses may have many minimal unsatisfiable
    subsets of different sizes.

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
    clauses = tuple(clauses)
    if sat(clauses):
        raise ValueError("Clauses are not unsatisfiable")

    def split(S):
        """
        Split S into two equal parts
        """
        S = tuple(S)
        L = len(S)//2
        return S[:L], S[L:]

    def minimal_unsat(clauses, include=()):
        """
        Return a minimal subset A of clauses such that A + include is
        unsatisfiable.

        Implicitly assumes that clauses + include is unsatisfiable.
        """
        # assert not sat(clauses + include), (len(clauses), len(include))

        # Base case: Since clauses + include is implicitly assumed to be
        # unsatisfiable, if clauses has only one element, it must be its own
        # minimal subset
        if len(clauses) == 1:
            return clauses

        A, B = split(clauses)

        # If one half is unsatisfiable (with include), we can discard the
        # other half.
        if not sat(A + include):
            return minimal_unsat(A, include)
        if not sat(B + include):
            return minimal_unsat(B, include)

        Astar = minimal_unsat(A, B + include)
        Bstar = minimal_unsat(B, Astar + include)
        return Astar + Bstar

    ret = minimal_unsat(clauses)
    return ret
