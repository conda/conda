import pycosat

from conda.logic import Linear, Clauses, true, false

def my_itersolve(iterable):
    """
    Work around https://github.com/ContinuumIO/pycosat/issues/13
    """
    iterable = [[i for i in j] for j in iterable]
    return pycosat.itersolve(iterable)

# TODO: We test that all the models of the transformed system are models of
# the original, but not that all models of the original are models of the
# transformed system.  Or does testing -x do this?

class NoBool(object):
    # Will only be called if tests are wrong and don't short-circuit correctly
    def __bool__(self):
        raise TypeError
    __nonzero__ = __bool__

def boolize(x):
    if x == true:
        return True
    if x == false:
        return False
    return NoBool()

def test_ITE():
    # Note, pycosat will automatically include all smaller numbers in models,
    # e.g., itersolve([[2]]) gives [[1, 2], [-1, 2]]. This should not be an
    # issue here.

    for c in [true, false, 1]:
        for t in [true, false, 2]:
            for f in [true, false, 3]:
                Cl = Clauses(3)
                x = Cl.ITE(c, t, f)
                if x in [true, false]:
                    if t == f:
                        # In this case, it doesn't matter if c is not boolizable
                        assert boolize(x) == boolize(t)
                    else:
                        assert boolize(x) == (boolize(t) if boolize(c) else
                            boolize(f)), (c, t, f)
                else:

                    for sol in my_itersolve({(x,)} | Cl.clauses):
                        C = boolize(c) if c in [true, false] else (1 in sol)
                        T = boolize(t) if t in [true, false] else (2 in sol)
                        F = boolize(f) if f in [true, false] else (3 in sol)
                        assert T if C else F, (T, C, F, sol, t, c, f)

                    for sol in my_itersolve({(-x,)} | Cl.clauses):
                        C = boolize(c) if c in [true, false] else (1 in sol)
                        T = boolize(t) if t in [true, false] else (2 in sol)
                        F = boolize(f) if f in [true, false] else (3 in sol)
                        assert not (T if C else F)

def test_And_clauses():
    # XXX: Is this i, j stuff necessary?
    for i in range(-1, 2, 2): # [-1, 1]
        for j in range(-1, 2, 2):
            C = Clauses(2)
            x = C.And(i*1, j*2)
            for sol in my_itersolve({(x,)} | C.clauses):
                f = i*1 in sol
                g = j*2 in sol
                assert f and g
            for sol in my_itersolve({(-x,)} | C.clauses):
                f = i*1 in sol
                g = j*2 in sol
                assert not (f and g)

    C = Clauses(1)
    x = C.And(1, -1)
    assert x == false # x and ~x
    assert C.clauses == set([])

    C = Clauses(1)
    x = C.And(1, 1)
    for sol in my_itersolve({(x,)} | C.clauses):
        f = 1 in sol
        assert (f and f)
    for sol in my_itersolve({(-x,)} | C.clauses):
        f = 1 in sol
        assert not (f and f)

def test_And_bools():
    for f in [true, false]:
        for g in [true, false]:
            C = Clauses(2)
            x = C.And(f, g)
            assert x == (true if (boolize(f) and boolize(g)) else false)
            assert C.clauses == set([])

        C = Clauses(1)
        x = C.And(f, 1)
        fb = boolize(f)
        if x in [true, false]:
            assert C.clauses == set([])
            xb = boolize(x)
            assert xb == (fb and NoBool())
        else:
            for sol in my_itersolve({(x,)} | C.clauses):
                a = 1 in sol
                assert (fb and a)
            for sol in my_itersolve({(-x,)} | C.clauses):
                a = 1 in sol
                assert not (fb and a)

        C = Clauses(1)
        x = C.And(1, f)
        if x in [true, false]:
            assert C.clauses == set([])
            xb = boolize(x)
            assert xb == (fb and NoBool())
        else:
            for sol in my_itersolve({(x,)} | C.clauses):
                a = 1 in sol
                assert (fb and a)
            for sol in my_itersolve({(-x,)} | C.clauses):
                a = 1 in sol
                assert not (fb and a)


def test_Or_clauses():
    # XXX: Is this i, j stuff necessary?
    for i in range(-1, 2, 2): # [-1, 1]
        for j in range(-1, 2, 2):
            C = Clauses(2)
            x = C.Or(i*1, j*2)
            for sol in my_itersolve({(x,)} | C.clauses):
                f = i*1 in sol
                g = j*2 in sol
                assert f or g
            for sol in my_itersolve({(-x,)} | C.clauses):
                f = i*1 in sol
                g = j*2 in sol
                assert not (f or g)

    C = Clauses(1)
    x = C.Or(1, -1)
    assert x == true # x or ~x
    assert C.clauses == set([])

    C = Clauses(1)
    x = C.Or(1, 1)
    for sol in my_itersolve({(x,)} | C.clauses):
        f = 1 in sol
        assert (f or f)
    for sol in my_itersolve({(-x,)} | C.clauses):
        f = 1 in sol
        assert not (f or f)


def test_Or_bools():
    for f in [true, false]:
        for g in [true, false]:
            C = Clauses(2)
            x = C.Or(f, g)
            assert x == (true if (boolize(f) or boolize(g)) else false)
            assert C.clauses == set([])

        C = Clauses(1)
        x = C.Or(f, 1)
        fb = boolize(f)
        if x in [true, false]:
            assert C.clauses == set([])
            xb = boolize(x)
            assert xb == (fb or NoBool())
        else:
            for sol in my_itersolve({(x,)} | C.clauses):
                a = 1 in sol
                assert (fb or a)
            for sol in my_itersolve({(-x,)} | C.clauses):
                a = 1 in sol
                assert not (fb or a)

        C = Clauses(1)
        x = C.Or(1, f)
        if x in [true, false]:
            assert C.clauses == set([])
            xb = boolize(x)
            assert xb == (fb or NoBool())
        else:
            for sol in my_itersolve({(x,)} | C.clauses):
                a = 1 in sol
                assert (fb or a)
            for sol in my_itersolve({(-x,)} | C.clauses):
                a = 1 in sol
                assert not (fb or a)

# Note xor is the same as !=
def test_Xor_clauses():
    # XXX: Is this i, j stuff necessary?
    for i in range(-1, 2, 2): # [-1, 1]
        for j in range(-1, 2, 2):
            C = Clauses(2)
            x = C.Xor(i*1, j*2)
            for sol in my_itersolve({(x,)} | C.clauses):
                f = i*1 in sol
                g = j*2 in sol
                assert (f != g)
            for sol in my_itersolve({(-x,)} | C.clauses):
                f = i*1 in sol
                g = j*2 in sol
                assert not (f != g)

    C = Clauses(1)
    x = C.Xor(1, 1)
    assert x == false # x xor x
    assert C.clauses == set([])

    C = Clauses(1)
    x = C.Xor(1, -1)
    assert x == true # x xor -x
    assert C.clauses == set([])

def test_Xor_bools():
    for f in [true, false]:
        for g in [true, false]:
            C = Clauses(2)
            x = C.Xor(f, g)
            assert x == (true if (boolize(f) != boolize(g)) else false)
            assert C.clauses == set([])

        C = Clauses(1)
        x = C.Xor(f, 1)
        fb = boolize(f)
        if x in [true, false]:
            assert False
        else:
            for sol in my_itersolve({(x,)} | C.clauses):
                a = 1 in sol
                assert (fb != a)
            for sol in my_itersolve({(-x,)} | C.clauses):
                a = 1 in sol
                assert not (fb != a)

        C = Clauses(1)
        x = C.Xor(1, f)
        if x in [true, false]:
            assert False
        else:
            for sol in my_itersolve({(x,)} | C.clauses):
                a = 1 in sol
                assert not (fb == a)
            for sol in my_itersolve({(-x,)} | C.clauses):
                a = 1 in sol
                assert not not (fb == a)

def test_true_false():
    assert true == true
    assert false == false
    assert true != false
    assert false != true
    assert -true == false
    assert -false == true

def test_Linear():
    l = Linear([(3, 1), (2, -4), (4, 5)], 12)
    l2 = Linear([(3, 1), (2, -4), (4, 5)], 12)
    l3 = Linear([(3, 2), (2, -4), (4, 5)], 12)
    l4 = Linear([(3, 1), (2, -4), (4, 5)], 11)
    assert l == l
    assert l == l2
    assert l != l3
    assert l != l4

    assert l.equation == [(2, -4), (3, 1), (4, 5)]
    assert l.lo == l.hi == l.rhs == 12
    assert l.coeffs == [2, 3, 4]
    assert l.atoms == [-4, 1, 5]
    assert l.total == 9

    assert len(l) == 3

    # Remember that the equation is sorted
    assert l[1:] == Linear([(3, 1), (4, 5)], 12)

    assert str(l) == repr(l) == "Linear([(2, -4), (3, 1), (4, 5)], 12)"

    l = Linear([(3, 1), (2, -4), (4, 5)], [3, 5])
    assert l != l2
    assert l != l3
    assert l != l4

    assert l.equation == [(2, -4), (3, 1), (4, 5)]
    assert l.lo == 3
    assert l.hi == 5
    assert l.rhs == [3, 5]
    assert l.coeffs == [2, 3, 4]
    assert l.atoms == [-4, 1, 5]
    assert l.total == 9

    assert len(l) == 3

    assert l([1, 2, 3, 4, 5]) == False
    assert l([1, 2, 3, 4, -5]) == True
    assert l([1, 2, 3, -4, -5]) == True
    assert l([-1, -2, -3, -4, -5]) == False
    assert l([-1, 2, 3, 4, -5]) == False

    # Remember that the equation is sorted
    assert l[1:] == Linear([(3, 1), (4, 5)], [3, 5])

    assert str(l) == repr(l) == "Linear([(2, -4), (3, 1), (4, 5)], [3, 5])"
    l = Linear([], [1, 3])
    assert l.equation == []
    assert l.lo == 1
    assert l.hi == 3
    assert l.coeffs == []
    assert l.atoms == []
    assert l.total == 0
    assert l([1, 2, 3]) == False

def test_BDD():
    L = [
        Linear([(1, 1), (2, 2)], [0, 2]),
        Linear([(1, 1), (2, -2)], [0, 2]),
        Linear([(1, 1), (2, 2), (3, 3)], [3, 3]),
        Linear([(0, 1), (1, 2), (2, 3), (0, 4), (1, 5), (0, 6), (1, 7)], [0, 2])
        ]
    for l in L:
        Cr = Clauses(max(l.atoms))
        xr = Cr.build_BDD_recursive(l)
        C = Clauses(max(l.atoms))
        x = C.build_BDD(l)
        assert x == xr
        assert C.clauses == Cr.clauses
        for sol in my_itersolve({(x,)} | C.clauses):
            assert l(sol)
        for sol in my_itersolve({(-x,)} | C.clauses):
            assert not l(sol)

    # Real life example. There are too many solutions to check them all, just
    # check that building the BDD doesn't take forever
    l = Linear([(1, 15), (2, 16), (3, 17), (4, 18), (5, 6), (5, 19), (6, 7),
    (6, 20), (7, 8), (7, 21), (7, 28), (8, 9), (8, 22), (8, 29), (8, 41), (9,
    10), (9, 23), (9, 30), (9, 42), (10, 1), (10, 11), (10, 24), (10, 31),
    (10, 34), (10, 37), (10, 43), (10, 46), (10, 50), (11, 2), (11, 12), (11,
    25), (11, 32), (11, 35), (11, 38), (11, 44), (11, 47), (11, 51), (12, 3),
    (12, 4), (12, 5), (12, 13), (12, 14), (12, 26), (12, 27), (12, 33), (12,
    36), (12, 39), (12, 40), (12, 45), (12, 48), (12, 49), (12, 52), (12, 53),
    (12, 54)], [192, 204])

    Cr = Clauses(max(l.atoms))
    xr = Cr.build_BDD_recursive(l)
    C = Clauses(max(l.atoms))
    x = C.build_BDD(l)
    assert x == xr
    assert C.clauses == Cr.clauses
    for _, sol in zip(range(20), my_itersolve({(x,)} | C.clauses)):
        assert l(sol)
    for _, sol in zip(range(20), my_itersolve({(-x,)} | C.clauses)):
        assert not l(sol)

    # Another real-life example. This one is too big to be built recursively
    # unless the recursion limit is increased.
    l = Linear([(0, 12), (0, 14), (0, 22), (0, 59), (0, 60), (0, 68), (0,
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
        (57, 107), (58, 106)], [21, 40])

    C = Clauses(max(l.atoms))
    x = C.build_BDD(l)
    for _, sol in zip(range(20), my_itersolve({(x,)} | C.clauses)):
        assert l(sol)
    for _, sol in zip(range(20), my_itersolve({(-x,)} | C.clauses)):
        assert not l(sol)
