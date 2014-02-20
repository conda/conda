import pycosat

from conda.logic import ITE, set_max_var, Linear, And, Or, Xor, true, false

# TODO: We test that all the models of the transformed system are models of
# the original, but not that all models of the original are models of the
# transformed system.

class NoBool(object):
    # Will only be called if tests are wrong and don't short-circuit correctly
    def __bool__(self):
        raise TypeError
    __nonzero__ = __bool__

def test_ITE_clauses():
    set_max_var(3)
    x, clauses = ITE(1, 2, 3)
    for sol in pycosat.itersolve([[x]] + clauses):
        c = 1 in sol
        t = 2 in sol
        f = 3 in sol
        assert t if c else f

    for sol in pycosat.itersolve([[-x]] + clauses):
        c = 1 in sol
        t = 2 in sol
        f = 3 in sol
        assert not (t if c else f)

def test_And_clauses():
    # XXX: Is this i, j stuff necessary?
    for i in range(-1, 2, 2): # [-1, 1]
        for j in range(-1, 2, 2):
            set_max_var(2)
            x, clauses = And(i*1, j*2)
            for sol in pycosat.itersolve([[x]] + clauses):
                f = i*1 in sol
                g = j*2 in sol
                assert f and g
            for sol in pycosat.itersolve([[-x]] + clauses):
                f = i*1 in sol
                g = j*2 in sol
                assert not (f and g)

    set_max_var(1)
    x, clauses = And(1, -1)
    assert x == false # x and ~x
    assert clauses == []

    set_max_var(1)
    x, clauses = And(1, 1)
    for sol in pycosat.itersolve([[x]] + clauses):
        f = 1 in sol
        assert (f and f)


def test_And_bools():
    for f in [true, false]:
        for g in [true, false]:
            set_max_var(2)
            x, clauses = And(f, g)
            assert x == true if (f == true and g == true) else false
            assert clauses == []

        set_max_var(1)
        x, clauses = And(f, 1)
        fb = (f == true)
        if x in [true, false]:
            assert clauses == []
            xb = (x == true)
            assert xb == (fb and NoBool())
        else:
            for sol in pycosat.itersolve([[x]] + clauses):
                a = 1 in sol
                assert (fb and a)

        set_max_var(1)
        x, clauses = And(1, f)
        fb = (f == true)
        if x in [true, false]:
            assert clauses == []
            xb = (x == true)
            assert xb == (fb and NoBool())
        else:
            for sol in pycosat.itersolve([[x]] + clauses):
                a = 1 in sol
                assert (fb and a)


def test_Or_clauses():
    # XXX: Is this i, j stuff necessary?
    for i in range(-1, 2, 2): # [-1, 1]
        for j in range(-1, 2, 2):
            set_max_var(2)
            x, clauses = Or(i*1, j*2)
            for sol in pycosat.itersolve([[x]] + clauses):
                f = i*1 in sol
                g = j*2 in sol
                assert f or g
            for sol in pycosat.itersolve([[-x]] + clauses):
                f = i*1 in sol
                g = j*2 in sol
                assert not (f or g)

    set_max_var(1)
    x, clauses = Or(1, -1)
    assert x == true # x or ~x
    assert clauses == []

    set_max_var(1)
    x, clauses = Or(1, 1)
    for sol in pycosat.itersolve([[x]] + clauses):
        f = 1 in sol
        assert (f or f)


def test_Or_bools():
    for f in [true, false]:
        for g in [true, false]:
            set_max_var(2)
            x, clauses = Or(f, g)
            assert x == true if (f == true or g == true) else false
            assert clauses == []

        set_max_var(1)
        x, clauses = Or(f, 1)
        fb = (f == true)
        if x in [true, false]:
            assert clauses == []
            xb = (x == true)
            assert xb == (fb or NoBool())
        else:
            for sol in pycosat.itersolve([[x]] + clauses):
                a = 1 in sol
                assert (fb or a)

        set_max_var(1)
        x, clauses = Or(1, f)
        fb = (f == true)
        if x in [true, false]:
            assert clauses == []
            xb = (x == true)
            assert xb == (fb or NoBool())
        else:
            for sol in pycosat.itersolve([[x]] + clauses):
                a = 1 in sol
                assert (fb or a)

# Note xor is the same as not ==
def test_Xor_clauses():
    # XXX: Is this i, j stuff necessary?
    for i in range(-1, 2, 2): # [-1, 1]
        for j in range(-1, 2, 2):
            set_max_var(2)
            x, clauses = Xor(i*1, j*2)
            for sol in pycosat.itersolve([[x]] + clauses):
                f = i*1 in sol
                g = j*2 in sol
                assert not (f == g)
            for sol in pycosat.itersolve([[-x]] + clauses):
                f = i*1 in sol
                g = j*2 in sol
                assert (f == g)

    set_max_var(1)
    x, clauses = Xor(1, 1)
    assert x == false # x xor x
    assert clauses == []

    set_max_var(1)
    x, clauses = Xor(1, -1)
    assert x == true # x xor -x
    assert clauses == []

def test_Xor_bools():
    for f in [true, false]:
        for g in [true, false]:
            set_max_var(2)
            x, clauses = Xor(f, g)
            assert x == true if not ((f == true) == (g == true)) else false
            assert clauses == []

        set_max_var(1)
        x, clauses = Xor(f, 1)
        fb = (f == true)
        if x in [true, false]:
            assert False
        else:
            for sol in pycosat.itersolve([[x]] + clauses):
                a = 1 in sol
                assert not (fb == a)

        set_max_var(1)
        x, clauses = Xor(1, f)
        fb = (f == true)
        if x in [true, false]:
            assert False
        else:
            for sol in pycosat.itersolve([[x]] + clauses):
                a = 1 in sol
                assert not (fb == a)

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
    assert l.lower_limit == 3
    assert l.upper_limit == 3

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
    assert l.lower_limit == -6
    assert l.upper_limit == -4

    assert len(l) == 3

    # Remember that the equation is sorted
    assert l[1:] == Linear([(3, 1), (4, 5)], [3, 5])

    assert str(l) == repr(l) == "Linear([(2, -4), (3, 1), (4, 5)], [3, 5])"
