import pycosat

from conda.logic import ITE, set_max_var, Linear

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
