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
        Linear([(1, 1), (2, 2), (3, 3)], [3, 3])
        ]
    for l in L:
        C = Clauses(max(l.atoms))
        x = C.build_BDD(l)
        for sol in my_itersolve({(x,)} | C.clauses):
            assert l(sol)
        for sol in my_itersolve({(-x,)} | C.clauses):
            assert not l(sol)
