# -*- coding: utf-8 -*-
"""\

The :class:`set` type brings the practical expressiveness of
set theory to Python. It has a very rich API overall, but lacks a
couple of fundamental features. For one, sets are not ordered. On top
of this, sets are not indexable, i.e, ``my_set[8]`` will raise an
:exc:`TypeError`. The :class:`IndexedSet` type remedies both of these
issues without compromising on the excellent complexity
characteristics of Python's built-in set implementation.
"""

from __future__ import print_function

from bisect import bisect_left
from itertools import chain, islice
from collections import MutableSet
import operator

try:
    from typeutils import make_sentinel
    _MISSING = make_sentinel(var_name='_MISSING')
except ImportError:
    _MISSING = object()


__all__ = ['IndexedSet']


_COMPACTION_FACTOR = 8

# TODO: inherit from set()
# TODO: .discard_many(), .remove_many()
# TODO: raise exception on non-set params?
# TODO: technically reverse operators should probably reverse the
# order of the 'other' inputs and put self last (to try and maintain
# insertion order)


class IndexedSet(MutableSet):
    """``IndexedSet`` is a :class:`collections.MutableSet` that maintains
    insertion order and uniqueness of inserted elements. It's a hybrid
    type, mostly like an OrderedSet, but also :class:`list`-like, in
    that it supports indexing and slicing.

    Args:
        other (iterable): An optional iterable used to initialize the set.

    >>> x = IndexedSet(list(range(4)) + list(range(8)))
    >>> x
    IndexedSet([0, 1, 2, 3, 4, 5, 6, 7])
    >>> x - set(range(2))
    IndexedSet([2, 3, 4, 5, 6, 7])
    >>> x[-1]
    7
    >>> fcr = IndexedSet('freecreditreport.com')
    >>> ''.join(fcr[:fcr.index('.')])
    'frecditpo'

    Standard set operators and interoperation with :class:`set` are
    all supported:

    >>> fcr & set('cash4gold.com')
    IndexedSet(['c', 'd', 'o', '.', 'm'])

    As you can see, the ``IndexedSet`` is almost like a ``UniqueList``,
    retaining only one copy of a given value, in the order it was
    first added. For the curious, the reason why IndexedSet does not
    support setting items based on index (i.e, ``__setitem__()``),
    consider the following dilemma::

      my_indexed_set = [A, B, C, D]
      my_indexed_set[2] = A

    At this point, a set requires only one *A*, but a :class:`list` would
    overwrite *C*. Overwriting *C* would change the length of the list,
    meaning that ``my_indexed_set[2]`` would not be *A*, as expected with a
    list, but rather *D*. So, no ``__setitem__()``.

    Otherwise, the API strives to be as complete a union of the
    :class:`list` and :class:`set` APIs as possible.
    """
    def __init__(self, other=None):
        self.item_index_map = dict()
        self.item_list = []
        self.dead_indices = []
        self._compactions = 0
        self._c_max_size = 0
        if other:
            self.update(other)

    # internal functions
    @property
    def _dead_index_count(self):
        return len(self.item_list) - len(self.item_index_map)

    def _compact(self):
        if not self.dead_indices:
            return
        self._compactions += 1
        dead_index_count = self._dead_index_count
        items, index_map = self.item_list, self.item_index_map
        self._c_max_size = max(self._c_max_size, len(items))
        for i, item in enumerate(self):
            items[i] = item
            index_map[item] = i
        del items[-dead_index_count:]
        del self.dead_indices[:]

    def _cull(self):
        ded = self.dead_indices
        if not ded:
            return
        items, ii_map = self.item_list, self.item_index_map
        if not ii_map:
            del items[:]
            del ded[:]
        elif len(ded) > 384:
            self._compact()
        elif self._dead_index_count > (len(items) / _COMPACTION_FACTOR):
            self._compact()
        elif items[-1] is _MISSING:  # get rid of dead right hand side
            num_dead = 1
            while items[-(num_dead + 1)] is _MISSING:
                num_dead += 1
            if ded and ded[-1][1] == len(items):
                del ded[-1]
            del items[-num_dead:]

    def _get_real_index(self, index):
        if index < 0:
            index += len(self)
        if not self.dead_indices:
            return index
        real_index = index
        for d_start, d_stop in self.dead_indices:
            if real_index < d_start:
                break
            real_index += d_stop - d_start
        return real_index

    def _add_dead(self, start, stop=None):
        # TODO: does not handle when the new interval subsumes
        # multiple existing intervals
        dints = self.dead_indices
        if stop is None:
            stop = start + 1
        cand_int = [start, stop]
        if not dints:
            dints.append(cand_int)
            return
        int_idx = bisect_left(dints, cand_int)
        dint = dints[int_idx - 1]
        d_start, d_stop = dint
        if start <= d_start <= stop:
            dint[0] = start
        elif start <= d_stop <= stop:
            dint[1] = stop
        else:
            dints.insert(int_idx, cand_int)
        return

    # common operations (shared by set and list)
    def __len__(self):
        return len(self.item_index_map)

    def __contains__(self, item):
        return item in self.item_index_map

    def __iter__(self):
        return (item for item in self.item_list if item is not _MISSING)

    def __reversed__(self):
        item_list = self.item_list
        return (item for item in reversed(item_list) if item is not _MISSING)

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, list(self))

    def __eq__(self, other):
        if isinstance(other, IndexedSet):
            return len(self) == len(other) and list(self) == list(other)
        return set(self) == set(other)

    @classmethod
    def from_iterable(cls, it):
        "from_iterable(it) -> create a set from an iterable"
        return cls(it)

    # set operations
    def add(self, item):
        "add(item) -> add item to the set"
        if item not in self.item_index_map:
            self.item_index_map[item] = len(self.item_list)
            self.item_list.append(item)

    def remove(self, item):
        "remove(item) -> remove item from the set, raises if not present"
        try:
            didx = self.item_index_map.pop(item)
        except KeyError:
            raise KeyError(item)
        self.item_list[didx] = _MISSING
        self._add_dead(didx)
        self._cull()

    def discard(self, item):
        "discard(item) -> discard item from the set (does not raise)"
        try:
            self.remove(item)
        except KeyError:
            pass

    def clear(self):
        "clear() -> empty the set"
        del self.item_list[:]
        del self.dead_indices[:]
        self.item_index_map.clear()

    def isdisjoint(self, other):
        "isdisjoint(other) -> return True if no overlap with other"
        iim = self.item_index_map
        for k in other:
            if k in iim:
                return False
        return True

    def issubset(self, other):
        "issubset(other) -> return True if other contains this set"
        if len(other) < len(self):
            return False
        for k in self.item_index_map:
            if k not in other:
                return False
        return True

    def issuperset(self, other):
        "issuperset(other) -> return True if set contains other"
        if len(other) > len(self):
            return False
        iim = self.item_index_map
        for k in other:
            if k not in iim:
                return False
        return True

    def union(self, *others):
        "union(*others) -> return a new set containing this set and others"
        return self.from_iterable(chain(self, *others))

    def iter_intersection(self, *others):
        "iter_intersection(*others) -> iterate over elements also in others"
        for k in self:
            for other in others:
                if k not in other:
                    break
            else:
                yield k
        return

    def intersection(self, *others):
        "intersection(*others) -> get a set with overlap of this and others"
        if len(others) == 1:
            other = others[0]
            return self.from_iterable(k for k in self if k in other)
        return self.from_iterable(self.iter_intersection(*others))

    def iter_difference(self, *others):
        "iter_difference(*others) -> iterate over elements not in others"
        for k in self:
            for other in others:
                if k in other:
                    break
            else:
                yield k
        return

    def difference(self, *others):
        "difference(*others) -> get a new set with elements not in others"
        if len(others) == 1:
            other = others[0]
            return self.from_iterable(k for k in self if k not in other)
        return self.from_iterable(self.iter_difference(*others))

    def symmetric_difference(self, *others):
        "symmetric_difference(*others) -> XOR set of this and others"
        ret = self.union(*others)
        return ret.difference(self.intersection(*others))

    __or__  = __ror__  = union
    __and__ = __rand__ = intersection
    __sub__ = __rsub__ = difference
    __xor__ = __rxor__ = symmetric_difference

    # in-place set operations
    def update(self, *others):
        "update(*others) -> add values from one or more iterables"
        if not others:
            return  # raise?
        elif len(others) == 1:
            other = others[0]
        else:
            other = chain(others)
        for o in other:
            self.add(o)

    def intersection_update(self, *others):
        "intersection_update(*others) -> discard self.difference(*others)"
        for val in self.difference(*others):
            self.discard(val)

    def difference_update(self, *others):
        "difference_update(*others) -> discard self.intersection(*others)"
        if self in others:
            self.clear()
        for val in self.intersection(*others):
            self.discard(val)

    def symmetric_difference_update(self, other):  # note singular 'other'
        "symmetric_difference_update(other) -> in-place XOR with other"
        if self is other:
            self.clear()
        for val in other:
            if val in self:
                self.discard(val)
            else:
                self.add(val)

    def __ior__(self, *others):
        self.update(*others)
        return self

    def __iand__(self, *others):
        self.intersection_update(*others)
        return self

    def __isub__(self, *others):
        self.difference_update(*others)
        return self

    def __ixor__(self, *others):
        self.symmetric_difference_update(*others)
        return self

    def iter_slice(self, start, stop, step=None):
        "iterate over a slice of the set"
        iterable = self
        if start is not None:
            start = self._get_real_index(start)
        if stop is not None:
            stop = self._get_real_index(stop)
        if step is not None and step < 0:
            step = -step
            iterable = reversed(self)
        return islice(iterable, start, stop, step)

    # list operations
    def __getitem__(self, index):
        try:
            start, stop, step = index.start, index.stop, index.step
        except AttributeError:
            index = operator.index(index)
        else:
            iter_slice = self.iter_slice(start, stop, step)
            return self.from_iterable(iter_slice)
        if index < 0:
            index += len(self)
        real_index = self._get_real_index(index)
        try:
            ret = self.item_list[real_index]
        except IndexError:
            raise IndexError('IndexedSet index out of range')
        return ret

    def pop(self, index=None):
        "pop(index) -> remove the item at a given index (-1 by default)"
        item_index_map = self.item_index_map
        len_self = len(item_index_map)
        if index is None or index == -1 or index == len_self - 1:
            ret = self.item_list.pop()
            del item_index_map[ret]
        else:
            real_index = self._get_real_index(index)
            ret = self.item_list[real_index]
            self.item_list[real_index] = _MISSING
            del item_index_map[ret]
            self._add_dead(real_index)
        self._cull()
        return ret

    def count(self, val):
        "count(val) -> count number of instances of value (0 or 1)"
        if val in self.item_index_map:
            return 1
        return 0

    def reverse(self):
        "reverse() -> reverse the contents of the set in-place"
        reversed_list = list(reversed(self))
        self.item_list[:] = reversed_list
        for i, item in enumerate(self.item_list):
            self.item_index_map[item] = i
        del self.dead_indices[:]

    def sort(self):
        "sort() -> sort the contents of the set in-place"
        sorted_list = sorted(self)
        if sorted_list == self.item_list:
            return
        self.item_list[:] = sorted_list
        for i, item in enumerate(self.item_list):
            self.item_index_map[item] = i
        del self.dead_indices[:]

    def index(self, val):
        "index(val) -> get the index of a value, raises if not present"
        try:
            return self.item_index_map[val]
        except KeyError:
            cn = self.__class__.__name__
            raise ValueError('%r is not in %s' % (val, cn))
