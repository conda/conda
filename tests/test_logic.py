from itertools import combinations, permutations, product

from conda.logic import (Clauses, true, false, evaluate_eq, minimal_unsatisfiable_subset)
from tests.helpers import raises

# These routines implement logical tests with short-circuiting
# and propogation of unknown values:
#    - positive integers are variables
#    - negative integers are negations of positive variables
#    - lowercase true and false are fixed values
#    - None reprents an indeterminate value
# If a fixed result is not determinable, the result is None, which
# propagates through the result.
#
# To ensure correctness, the only logic functions we have implemented
# directly are NOT and OR. The rest are implemented in terms of these.
# Peformance is not an issue.

def my_NOT(x):
    return None if x is None else -x

def my_OR(*args):
    '''Implements a logical OR according to the logic:
            - positive integers are variables
            - negative integers are negations of positive variables
            - lowercase true and false are fixed values
            - None is an unknown value
       true  OR x -> true
       false OR x -> false
       None  OR x -> None
       x     OR y -> None'''
    if any(v is true for v in args):
        return true
    args = set([v for v in args if v is not false])
    if len(args) == 0:
        return false
    if len(args) == 1:
        return next(v for v in args)
    if len(set([v if v is None else abs(v) for v in args])) < len(args):
        return true
    return None

def my_AND(*args):
    args = list(map(my_NOT,args))
    return my_NOT(my_OR(*args))

def my_XOR(i,j):
    return my_OR(my_AND(i,-j),my_AND(-i,j))

def my_ITE(c,t,f):
    return my_OR(my_AND(c,t),my_AND(-c,f))

def my_AMONE(*args):
    args = [my_NOT(v) for v in args]
    return my_AND(*[my_OR(v1,v2) for v1,v2 in combinations(args,2)])

def my_XONE(*args):
    return my_AND(my_OR(*args),my_AMONE(*args))

def my_SOL(ij, sol):
    return (v if v in (true, false) else (true if v in sol else false) for v in ij)

def my_EVAL(eq, sol):
    # evaluate_eq doesn't handle true/false entries
    return evaluate_eq(eq, sol) + sum(c for c, a in eq if a is true)

# Testing strategy: mechanically construct a all possible permutations of
# true, false, variables from 1 to m, and their negations, in order to exercise
# all logical branches of the function. Test negative, positive, and full
# polarities for each.

def my_TEST(Mfunc, Cfunc, mmin, mmax, is_iter):
    for m in range(mmin,mmax+1):
        if m == 0:
            ijprod = [()]
        else:
            ijprod = (true,false)+sum(((k,-k) for k in range(1,m+1)),())
            ijprod = product(ijprod, repeat=m)
        for ij in ijprod:
            tsol = Mfunc(*ij)
            for polarity in (True, False, None):
                C = Clauses(m)
                Cmethod = Cfunc.__get__(C,Clauses)
                if is_iter:
                    x = Cmethod(ij, polarity=polarity)
                else:
                    x = Cmethod(*ij, polarity=polarity)
                if tsol is not None:
                    assert x == tsol, (ij,Cfunc.__name__,polarity,C.clauses)
                    continue
                if polarity in {True, None}:
                    for sol in C.itersolve([(x,)],m):
                        qsol = Mfunc(*my_SOL(ij,sol))
                        assert qsol is true, (ij,sol,Cfunc.__name__,polarity,C.clauses)
                if polarity in {False, None}:
                    for sol in C.itersolve([(-x,)],m):
                        qsol = Mfunc(*my_SOL(ij,sol))
                        assert qsol is false, (ij,sol,Cfunc.__name__,polarity,C.clauses)

def test_true_false():
    assert str(true) == "true"
    assert str(false) == "false"
    assert hash(true) != hash(false)

    assert true == true
    assert false == false
    assert true != false
    assert false != true
    assert -true == false
    assert -false == true

    assert false < true
    assert not (true < false)
    assert not (false < false)
    assert not (true < true)
    assert false <= true
    assert true <= true
    assert false <= false
    assert true <= true

    assert not (false > true)
    assert true > false
    assert not (false > false)
    assert not (true > true)
    assert not (false >= true)
    assert (true >= true)
    assert false >= false
    assert true >= true

def test_AND():
    my_TEST(my_AND, Clauses.And, 2,2, False)
    my_TEST(my_AND, Clauses.All, 0,4, True)

def test_OR():
    my_TEST(my_OR,  Clauses.Or,  2,2, False)
    my_TEST(my_OR,  Clauses.Any, 0,4, True)

def test_XOR():
    my_TEST(my_XOR, Clauses.Xor, 2,2, False)

def test_ITE():
    my_TEST(my_ITE, Clauses.ITE, 3,3, False)

def test_AMONE():
    my_TEST(my_AMONE, Clauses.AtMostOne_1, 0,3, True)
    my_TEST(my_AMONE, Clauses.AtMostOne_2, 0,3, True)
    my_TEST(my_AMONE, Clauses.AtMostOne, 0,3, True)

def test_XONE():
    my_TEST(my_XONE, Clauses.ExactlyOne_1, 0,3, True)
    my_TEST(my_XONE, Clauses.ExactlyOne_2, 0,3, True)
    my_TEST(my_XONE, Clauses.ExactlyOne, 0,3, True)

def test_Require_False():
    C = Clauses(1)
    C.Require(C.And, 1, -1)
    assert C.sat() is None

def test_LinearBound():
    L = [
        ([], [0, 1], true),
        ([], [1, 2], false),
        ([(2, 1), (2, 2)], [3, 3], false),
        ([(2, 1), (2, 2)], [0, 1], 1000),
        ([(1, 1), (2, 2)], [0, 2], 1000),
        ([(1, 1), (2, -2)], [0, 2], 1000),
        ([(1, 1), (2, 2), (3, 3)], [3, 3], 1000),
        ([(0, 1), (1, 2), (2, 3), (0, 4), (1, 5), (0, 6), (1, 7)], [0, 2], 1000),
        ([(0, 1), (1, 2), (2, 3), (0, 4), (1, 5), (0, 6), (1, 7), 
          (3, false), (2, true)], [2, 4], 1000),
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
        N = max([0]+[a for c,a in eq if a is not true and a is not false])
        C = Clauses(N)
        Cneg = Clauses(N)
        Cpos = Clauses(N)
        x = C.LinearBound(eq, rhs[0], rhs[1])
        xneg = Cneg.LinearBound(eq, rhs[0], rhs[1], polarity=False)
        xpos = Cpos.LinearBound(eq, rhs[0], rhs[1], polarity=True)
        if max_iter is true or max_iter is false:
            assert x == max_iter
            assert xneg == max_iter
            assert xpos == max_iter
            continue
        for _, sol in zip(range(max_iter), C.itersolve([(x,)],N)):
            assert rhs[0] <= my_EVAL(eq,sol) <= rhs[1]
        for _, sol in zip(range(max_iter), Cpos.itersolve([(xpos,)],N)):
            assert rhs[0] <= my_EVAL(eq,sol) <= rhs[1]
        for _, sol in zip(range(max_iter), C.itersolve([(-x,)],N)):
            assert not(rhs[0] <= my_EVAL(eq,sol) <= rhs[1])
        for _, sol in zip(range(max_iter), C.itersolve([(-xneg,)],N)):
            assert not(rhs[0] <= my_EVAL(eq,sol) <= rhs[1])

def test_sat():
    def sat(val, m=1):
        return Clauses(m).sat(val)
    assert sat([[1]]) == [1]
    assert sat([[1], [-1]]) is None
    assert sat([]) == [1]

def test_minimal_unsatisfiable_subset():
    def sat(val):
        return Clauses().sat(val)
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
