"""
The basic idea to nest logical expressions is instead of trying to denest
things via distribution, we add new variables. So if we have some logical
expression expr, we replace it with x and add expr <-> x to the clauses,
where x is a new variable, and expr <-> x is recursively evaluated in the
same way, so that the final clauses are ORs of atoms.
"""

# Global state? Really?

global MAX_N
MAX_N = 0

def get_new_var():
    global MAX_N
    new_var = MAX_N = MAX_N + 1
    return new_var

def set_max_var(m):
    global MAX_N
    MAX_N = m

# All functions return the tuple (new_var, new_clauses). new_var is a literal
# that should be used in place of the expression. new_clauses should be added
# to the clauses of the SAT solver.

# All functions take atoms as arguments, that is, it is the callers'
# responsibility to do the conversion of expressions recursively. This is done
# because we do not have data structures representing the various logical
# classes, only atoms.


# TODO: Take advantage of polarity, meaning that we can add only one direction
# of the implication, expr -> x or expr <- x, depending on how expr appears.

def ITE(c, t, f):
    """
    if c then t else f
    """
    # Basically, c ? t : f is equivalent to (c AND t) OR (NOT c AND f)

    x = get_new_var()
    # "Red" clauses are redundant, but they assist the unit propagation in the
    # SAT solver
    new_clauses = [
        # Negative
        [-c, -t, x],
        [c, -f, x],
        [-t, -f, x], # Red
        # Positive
        [-c, t, -x],
        [c, f, -x],
        [t, f, -x], # Red
    ]

    return (x, new_clauses)
