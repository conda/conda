from itertools import combinations, permutations, product

import pycosat
from conda.logic import (Clauses, true, false, evaluate_eq, minimal_unsatisfiable_subset)

from tests.helpers import raises

def my_itersolve(iterable):
    """
    Work around https://github.com/ContinuumIO/pycosat/issues/13
    """
    iterable = [[i for i in j] for j in iterable]
    return pycosat.itersolve(iterable)

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
                    for sol in my_itersolve([(x,)] + C.clauses):
                        qsol = Mfunc(*my_SOL(ij,sol))
                        assert qsol is true, (ij,sol,Cfunc.__name__,polarity,C.clauses)
                if polarity in {False, None}:
                    for sol in my_itersolve([(-x,)] + C.clauses):
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
    my_TEST(my_AMONE, Clauses.AtMostOne, 0,3, True)

def test_XONE():
    my_TEST(my_XONE, Clauses.ExactlyOne, 0,3, True)

def test_Require_False():
    C = Clauses(1)
    C.Require(C.And, 1, -1)
    assert C.sat() is None

def test_LinearBound():
    L = [
        ([], [0,1], true),
        ([], [1,2], false),
        ([(2, 1), (2, 2)], [3, 3], false),
        ([(2, 1), (2, 2)], [0, 1], 1000),
        ([(1, 1), (2, 2)], [0, 2], 1000),
        ([(1, 1), (2, -2)], [0, 2], 1000),
        ([(1, 1), (2, 2), (3, 3)], [3, 3], 1000),
        ([(0, 1), (1, 2), (2, 3), (0, 4), (1, 5), (0, 6), (1, 7)], [0, 2], 10000),
        ([(1, 15), (2, 16), (3, 17), (4, 18), (5, 6), (5, 19), (6, 7),
          (6, 20), (7, 8), (7, 21), (7, 28), (8, 9), (8, 22), (8, 29), (8, 41), (9,
          10), (9, 23), (9, 30), (9, 42), (10, 1), (10, 11), (10, 24), (10, 31),
          (10, 34), (10, 37), (10, 43), (10, 46), (10, 50), (11, 2), (11, 12), (11,
          25), (11, 32), (11, 35), (11, 38), (11, 44), (11, 47), (11, 51), (12, 3),
          (12, 4), (12, 5), (12, 13), (12, 14), (12, 26), (12, 27), (12, 33), (12,
          36), (12, 39), (12, 40), (12, 45), (12, 48), (12, 49), (12, 52), (12, 53),
          (12, 54)], [192, 204], 100),
        ([(0, 12), (0, 14), (0, 22), (0, 59), (0, 60), (0, 68), (0,
        102), (0, 105), (0, 164), (0, 176), (0, 178), (0, 180), (0, 182), (1,
            9), (1, 13), (1, 21), (1, 58), (1, 67), (1, 101), (1, 104), (1,
                163), (1, 175), (1, 177), (1, 179), (1, 181), (2, 6), (2, 20),
        (2, 57), (2, 66), (2, 100), (2, 103), (2, 162), (2, 174), (3, 11), (3,
            19), (3, 56), (3, 65), (3, 99), (3, 161), (3, 173), (4, 8), (4,
                18), (4, 55), (4, 64), (4, 98), (4, 160), (4, 172), (5, 5),
        (5, 17), (5, 54), (5, 63), (5, 97), (5, 159), (5, 171), (6, 10), (6,
            16), (6, 52), (6, 62), (6, 96), (6, 158), (6, 170), (7, 7), (7,
                15), (7, 50), (7, 61), (7, 95), (7, 157), (7, 169), (8, 4),
        (8, 48), (8, 94), (8, 156), (8, 168), (9, 3), (9, 46), (9, 93), (9,
            155), (9, 167), (10, 2), (10, 53), (10, 92), (10, 154), (10, 166),
        (11, 1), (11, 51), (11, 91), (11, 152), (11, 165), (12, 49), (12, 90),
        (12, 150), (13, 47), (13, 89), (13, 148), (14, 45), (14, 88), (14,
            146), (15, 39), (15, 87), (15, 144), (16, 38), (16, 86), (16,
                142), (17, 37), (17, 85), (17, 140), (18, 44), (18, 84), (18,
                    138), (19, 43), (19, 83), (19, 153), (20, 42), (20, 82),
        (20, 151), (21, 41), (21, 81), (21, 149), (22, 40), (22, 80), (22,
            147), (23, 36), (23, 79), (23, 145), (24, 32), (24, 70), (24,
                143), (25, 35), (25, 78), (25, 141), (26, 34), (26, 77), (26,
                    139), (27, 31), (27, 76), (27, 137), (28, 30), (28, 75),
        (28, 136), (29, 33), (29, 74), (29, 135), (30, 29), (30, 73), (30,
            134), (31, 28), (31, 72), (31, 133), (32, 27), (32, 71), (32,
                132), (33, 25), (33, 69), (33, 131), (34, 24), (34, 130), (35,
                    26), (35, 129), (36, 23), (36, 128), (37, 125), (38, 124),
        (39, 123), (40, 122), (41, 121), (42, 120), (43, 119), (44, 118), (45,
            117), (46, 116), (47, 115), (48, 114), (49, 113), (50, 127), (51,
                126), (52, 112), (53, 111), (54, 110), (55, 109), (56, 108),
        (57, 107), (58, 106)], [21, 40], 100)
        ]
    for eq, rhs, max_iter in L:
        N = max([0]+[a for c,a in eq])
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
        for _, sol in zip(range(max_iter), my_itersolve([(x,)] + C.clauses)):
            assert rhs[0] <= evaluate_eq(eq,sol) <= rhs[1]
        for _, sol in zip(range(max_iter), my_itersolve([(xpos,)] + Cpos.clauses)):
            assert rhs[0] <= evaluate_eq(eq,sol) <= rhs[1]
        for _, sol in zip(range(max_iter), my_itersolve([(-x,)] + C.clauses)):
            assert not(rhs[0] <= evaluate_eq(eq,sol) <= rhs[1])
        for _, sol in zip(range(max_iter), my_itersolve([(-xneg,)] + Cneg.clauses)):
            assert not(rhs[0] <= evaluate_eq(eq,sol) <= rhs[1])

def test_sat():
    def sat(val):
        return Clauses().sat(val)
    assert sat([[1]]) == [1]
    assert sat([[1], [-1]]) is None
    assert sat([]) == []

def test_minimal_unsatisfiable_subset():
    def sat(val):
        return Clauses().sat(val)
    assert raises(ValueError, lambda: minimal_unsatisfiable_subset([[1]], sat))

    clauses = [[-10], [1], [5], [2, 3], [3, 4], [5, 2], [-7], [2], [3], [-2,
        -3, 5], [7, 8, 9, 10], [-8], [-9]]
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
