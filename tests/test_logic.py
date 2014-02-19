import pycosat

from logic import ITE, set_max_var

def test_ITE():
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
