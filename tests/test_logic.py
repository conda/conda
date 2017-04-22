from itertools import combinations, permutations, product, chain

import pytest

from conda.logic import (Clauses, evaluate_eq, minimal_unsatisfiable_subset)
from tests.helpers import raises
from conda.common.compat import string_types, iteritems

# These routines implement logical tests with short-circuiting
# and propogation of unknown values:
#    - positive integers are variables
#    - negative integers are negations of positive variables
#    - lowercase True and False are fixed values
#    - None reprents an indeterminate value
# If a fixed result is not determinable, the result is None, which
# propagates through the result.
#
# To ensure correctness, the only logic functions we have implemented
# directly are NOT and OR. The rest are implemented in terms of these.
# Peformance is not an issue.


def my_NOT(x):
    if isinstance(x, bool):
        return not x
    if isinstance(x, int):
        return -x
    if isinstance(x, string_types):
        return x[1:] if x[0] == '!' else '!' + x
    return None


def my_ABS(x):
    if isinstance(x, bool):
        return True
    if isinstance(x, int):
        return abs(x)
    if isinstance(x, string_types):
        return x[1:] if x[0] == '!' else x
    return None


def my_OR(*args):
    '''Implements a logical OR according to the logic:
            - positive integers are variables
            - negative integers are negations of positive variables
            - lowercase True and False are fixed values
            - None is an unknown value
       True  OR x -> True
       False OR x -> False
       None  OR x -> None
       x     OR y -> None'''
    if any(v is True for v in args):
        return True
    args = set([v for v in args if v is not False])
    if len(args) == 0:
        return False
    if len(args) == 1:
        return next(v for v in args)
    if len(set([v if v is None else my_ABS(v) for v in args])) < len(args):
        return True
    return None


def my_AND(*args):
    args = list(map(my_NOT,args))
    return my_NOT(my_OR(*args))


def my_XOR(i,j):
    return my_OR(my_AND(i,my_NOT(j)),my_AND(my_NOT(i),j))


def my_ITE(c,t,f):
    return my_OR(my_AND(c,t),my_AND(my_NOT(c),f))


def my_AMONE(*args):
    args = [my_NOT(v) for v in args]
    return my_AND(*[my_OR(v1,v2) for v1,v2 in combinations(args,2)])


def my_XONE(*args):
    return my_AND(my_OR(*args),my_AMONE(*args))


def my_SOL(ij, sol):
    return (v if type(v) is bool else (True if v in sol else False) for v in ij)


def my_EVAL(eq, sol):
    # evaluate_eq doesn't handle True/False entries
    return evaluate_eq(eq, sol) + sum(c for c, a in eq if a is True)

# Testing strategy: mechanically construct a all possible permutations of
# True, False, variables from 1 to m, and their negations, in order to exercise
# all logical branches of the function. Test negative, positive, and full
# polarities for each.


def my_TEST(Mfunc, Cfunc, mmin, mmax, is_iter):
    for m in range(mmin,mmax+1):
        if m == 0:
            ijprod = [()]
        else:
            ijprod = (True,False)+sum(((k,my_NOT(k)) for k in range(1,m+1)),())
            ijprod = product(ijprod, repeat=m)
        for ij in ijprod:
            C = Clauses()
            Cpos = Clauses()
            Cneg = Clauses()
            for k in range(1,m+1):
                nm = 'x%d' % k
                C.new_var(nm)
                Cpos.new_var(nm)
                Cneg.new_var(nm)
            ij2 = tuple(C.from_index(k) if type(k) is int else k for k in ij)
            if is_iter:
                x = Cfunc.__get__(C,Clauses)(ij2)
                Cpos.Require(Cfunc.__get__(Cpos,Clauses), ij)
                Cneg.Prevent(Cfunc.__get__(Cneg,Clauses), ij)
            else:
                x = Cfunc.__get__(C,Clauses)(*ij2)
                Cpos.Require(Cfunc.__get__(Cpos,Clauses), *ij)
                Cneg.Prevent(Cfunc.__get__(Cneg,Clauses), *ij)
            tsol = Mfunc(*ij)
            if type(tsol) is bool:
                assert x is tsol, (ij2, Cfunc.__name__, C.clauses)
                assert Cpos.unsat == (not tsol) and not Cpos.clauses, (ij, 'Require(%s)')
                assert Cneg.unsat == tsol and not Cneg.clauses, (ij, 'Prevent(%s)')
                continue
            for sol in C.itersolve([(x,)]):
                qsol = Mfunc(*my_SOL(ij,sol))
                assert qsol is True, (ij2, sol, Cfunc.__name__, C.clauses)
            for sol in Cpos.itersolve([]):
                qsol = Mfunc(*my_SOL(ij,sol))
                assert qsol is True, (ij, sol,'Require(%s)' % Cfunc.__name__, Cpos.clauses)
            for sol in C.itersolve([(C.Not(x),)]):
                qsol = Mfunc(*my_SOL(ij,sol))
                assert qsol is False, (ij2, sol, Cfunc.__name__, C.clauses)
            for sol in Cneg.itersolve([]):
                qsol = Mfunc(*my_SOL(ij,sol))
                assert qsol is False, (ij, sol,'Prevent(%s)' % Cfunc.__name__, Cneg.clauses)


def test_NOT():
    my_TEST(my_NOT, Clauses.Not, 1, 1, False)


def test_AND():
    my_TEST(my_AND, Clauses.And, 2,2, False)


@pytest.mark.integration  # only because this test is slow
def test_ALL():
    my_TEST(my_AND, Clauses.All, 0, 4, True)


def test_OR():
    my_TEST(my_OR,  Clauses.Or,  2,2, False)


@pytest.mark.integration  # only because this test is slow
def test_ANY():
    my_TEST(my_OR,  Clauses.Any, 0,4, True)


def test_XOR():
    my_TEST(my_XOR, Clauses.Xor, 2,2, False)


def test_ITE():
    my_TEST(my_ITE, Clauses.ITE, 3,3, False)


def test_AMONE():
    my_TEST(my_AMONE, Clauses.AtMostOne_NSQ, 0,3, True)
    my_TEST(my_AMONE, Clauses.AtMostOne_BDD, 0,3, True)
    my_TEST(my_AMONE, Clauses.AtMostOne, 0,3, True)
    C1 = Clauses(10)
    x1 = C1.AtMostOne_BDD((1,2,3,4,5,6,7,8,9,10))
    C2 = Clauses(10)
    x2 = C2.AtMostOne((1,2,3,4,5,6,7,8,9,10))
    assert x1 == x2 and C1.clauses == C2.clauses


@pytest.mark.integration  # only because this test is slow
def test_XONE():
    my_TEST(my_XONE, Clauses.ExactlyOne_NSQ, 0,3, True)
    my_TEST(my_XONE, Clauses.ExactlyOne_BDD, 0,3, True)
    my_TEST(my_XONE, Clauses.ExactlyOne, 0,3, True)


@pytest.mark.integration  # only because this test is slow
def test_LinearBound():
    L = [
        ([], [0, 1], 10),
        ([], [1, 2], 10),
        ({'x1':2, 'x2':2}, [3, 3], 10),
        ({'x1':2, 'x2':2}, [0, 1], 1000),
        ({'x1':1, 'x2':2}, [0, 2], 1000),
        ({'x1':2, '!x2':2}, [0, 2], 1000),
        ([(1, 1), (2, 2), (3, 3)], [3, 3], 1000),
        ([(0, 1), (1, 2), (2, 3), (0, 4), (1, 5), (0, 6), (1, 7)], [0, 2], 1000),
        ([(0, 1), (1, 2), (2, 3), (0, 4), (1, 5), (0, 6), (1, 7),
          (3, False), (2, True)], [2, 4], 1000),
        ([(1, 15), (2, 16), (3, 17), (4, 18), (5, 6), (5, 19), (6, 7),
          (6, 20), (7, 8), (7, 21), (7, 28), (8, 9), (8, 22), (8, 29), (8, 41), (9,
          10), (9, 23), (9, 30), (9, 42), (10, 1), (10, 11), (10, 24), (10, 31),
          (10, 34), (10, 37), (10, 43), (10, 46), (10, 50), (11, 2), (11, 12), (11,
          25), (11, 32), (11, 35), (11, 38), (11, 44), (11, 47), (11, 51), (12, 3),
          (12, 4), (12, 5), (12, 13), (12, 14), (12, 26), (12, 27), (12, 33), (12,
          36), (12, 39), (12, 40), (12, 45), (12, 48), (12, 49), (12, 52), (12, 53),
          (12, 54)], [192, 204], 100),
        ]
    for eq, rhs, max_iter in L:
        if isinstance(eq, dict):
            N = len(eq)
        else:
            N = max([0]+[a for c,a in eq if a is not True and a is not False])
        C = Clauses(N)
        Cpos = Clauses(N)
        Cneg = Clauses(N)
        if isinstance(eq, dict):
            for k in range(1,N+1):
                nm = 'x%d'%k
                C.name_var(k, nm)
                Cpos.name_var(k, nm)
                Cneg.name_var(k, nm)
            eq2 = [(v,C.from_name(c)) for c,v in iteritems(eq)]
        else:
            eq2 = eq
        x = C.LinearBound(eq, rhs[0], rhs[1])
        Cpos.Require(Cpos.LinearBound, eq, rhs[0], rhs[1])
        Cneg.Prevent(Cneg.LinearBound, eq, rhs[0], rhs[1])
        if x is not False:
            for _, sol in zip(range(max_iter), C.itersolve([] if x is True else [(x,)],N)):
                assert rhs[0] <= my_EVAL(eq2,sol) <= rhs[1], C.clauses
        if x is not True:
            for _, sol in zip(range(max_iter), C.itersolve([] if x is True else [(C.Not(x),)],N)):
                assert not(rhs[0] <= my_EVAL(eq2,sol) <= rhs[1]), C.clauses
        for _, sol in zip(range(max_iter), Cpos.itersolve([],N)):
            assert rhs[0] <= my_EVAL(eq2,sol) <= rhs[1], ('Cpos',Cpos.clauses)
        for _, sol in zip(range(max_iter), Cneg.itersolve([],N)):
            assert not(rhs[0] <= my_EVAL(eq2,sol) <= rhs[1]), ('Cneg',Cneg.clauses)


def test_sat():
    C = Clauses()
    C.new_var('x1')
    C.new_var('x2')
    assert C.sat() is not None
    assert C.sat([]) is not None
    assert C.sat([()]) is None
    assert C.sat([(False,)]) is None
    assert C.sat([(True,),()]) is None
    assert C.sat([(True,False,-1)]) is not None
    assert C.sat([(+1,False),(+2,),(True,)], names=True) == {'x1','x2'}
    assert C.sat([(-1,False),(True,),(+2,)], names=True) == {'x2'}
    assert C.sat([(True,),(-1,),(-2,False)], names=True) == set()
    assert C.sat([(+1,),(-1,False)], names=True) is None
    C.unsat = True
    assert C.sat() is None
    assert C.sat([]) is None
    assert C.sat([(True,)]) is None
    assert len(Clauses(10).sat([[1]])) == 10


def test_minimize():
    # minimize    x1 + 2 x2 + 3 x3 + 4 x4 + 5 x5
    # subject to  x1 + x2 + x3 + x4 + x5  == 1
    C = Clauses(15)
    C.Require(C.ExactlyOne, range(1,6))
    sol = C.sat()
    C.unsat = True
    # Unsatisfiable constraints
    assert C.minimize([(k,k) for k in range(1,6)], sol)[1] == 16
    C.unsat = False
    sol, sval = C.minimize([(k,k) for k in range(1,6)], sol)
    assert sval == 1
    C.Require(C.ExactlyOne, range(6,11))
    # Supply an initial vector that is too short, forcing recalculation
    sol, sval = C.minimize([(k,k) for k in range(6,11)], sol)
    assert sval == 6
    C.Require(C.ExactlyOne, range(11,16))
    # Don't supply an initial vector
    sol, sval = C.minimize([(k,k) for k in range(11,16)])
    assert sval == 11


def test_minimal_unsatisfiable_subset():
    def sat(val):
        return Clauses(max(abs(v) for v in chain(*val))).sat(val)
    assert raises(ValueError, lambda: minimal_unsatisfiable_subset([[1]], sat))

    clauses = [[-10], [1], [5], [2, 3], [3, 4], [5, 2], [-7], [2], [3],
        [-2, -3, 5], [7, 8, 9, 10], [-8], [-9]]
    res = minimal_unsatisfiable_subset(clauses, sat)
    assert sorted(res) == [[-10], [-9], [-8], [-7], [7, 8, 9, 10]]
    assert not sat(res)

    clauses = [[1, 3], [2, 3], [-1], [4], [3], [-3]]
    for perm in permutations(clauses):
        res = minimal_unsatisfiable_subset(clauses, sat)
        assert sorted(res) == [[-3], [3]]
        assert not sat(res)

    clauses = [[1], [-1], [2], [-2], [3, 4], [4]]
    for perm in permutations(clauses):
        res = minimal_unsatisfiable_subset(perm, sat)
        assert sorted(res) in [[[-1], [1]], [[-2], [2]]]
        assert not sat(res)
