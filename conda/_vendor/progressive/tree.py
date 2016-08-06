from __future__ import division

from copy import deepcopy

from .bar import Bar
from .cursor import Cursor
from .util import floor, ensure, merge_dicts
from .exceptions import LengthOverflowError
from .widgets import ETA, FileTransferSpeed

class Value(object):
    """Container class for use with ``BarDescriptor``

    Should be used for ``value`` argument when initializing
        ``BarDescriptor``, e.g., ``BarDescriptor(type=..., value=Value(10))``
    """

    def __init__(self, val=0):
        self._value = val

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, val):
        self._value = floor(val)


class BarDescriptor(dict):
    """Bar descriptor

    To be used in leaf of a tree describing a hierarchy for ``ProgressTree``,
    e.g.,:

        tree = {"Job":
            {"Task1": BarDescriptor(...)},
            {"Task2":
                {"Subtask1": BarDescriptor(...)},
            },
        }

    :type  type: Bar|subclass of Bar
    :param type: The type of Bar to use to display that leaf
    :type  value: Value
    :param value: Amount to fill the progress bar vs. its max value
    :type  args: list
    :param args: A list of args to instantiate ``type`` with
    :type  kwargs: dict
    :param kwargs: A dict of kwargs to instantiate ``type`` with
    """


class ProgressTree(object):
    """Progress display for trees

    For drawing a hierarchical progress view from a tree

    :type  term: NoneType|blessings.Terminal
    :param term: Terminal instance; if not given, will be created by the class
    :type  indent: int
    :param indent: The amount of indentation between each level in hierarchy
    """

    def __init__(self, term=None, indent=4):
        self.cursor = Cursor(term)
        self.indent = indent

    ##################
    # Public Methods #
    ##################

    def draw(self, tree, bar_desc=None, save_cursor=True, flush=True):
        """Draw ``tree`` to the terminal

        :type  tree: dict
        :param tree: ``tree`` should be a tree representing a hierarchy; each
            key should be a string describing that hierarchy level and value
            should also be ``dict`` except for leaves which should be
            ``BarDescriptors``. See ``BarDescriptor`` for a tree example.
        :type  bar_desc: BarDescriptor|NoneType
        :param bar_desc: For describing non-leaf bars in that will be
            drawn from ``tree``; certain attributes such as ``value``
            and ``kwargs["max_value"]`` will of course be overridden
            if provided.
        :type  flush: bool
        :param flush: If this is set, output written will be flushed
        :type  save_cursor: bool
        :param save_cursor: If this is set, cursor location will be saved before
            drawing; this will OVERWRITE a previous save, so be sure to set
            this accordingly (to your needs).
        """
        if save_cursor:
            self.cursor.save()

        tree = deepcopy(tree)
        # TODO: Automatically collapse hierarchy so something
        #   will always be displayable (well, unless the top-level)
        #   contains too many to display
        lines_required = self.lines_required(tree)
        ensure(lines_required <= self.cursor.term.height,
               LengthOverflowError,
               "Terminal is not long ({} rows) enough to fit all bars "
               "({} rows).".format(self.cursor.term.height, lines_required))
        bar_desc = BarDescriptor(type=Bar) if not bar_desc else bar_desc
        self._calculate_values(tree, bar_desc)
        self._draw(tree)
        if flush:
            self.cursor.flush()

    def make_room(self, tree):
        """Clear lines in terminal below current cursor position as required

        This is important to do before drawing to ensure sufficient
        room at the bottom of your terminal.

        :type  tree: dict
        :param tree: tree as described in ``BarDescriptor``
        """
        lines_req = self.lines_required(tree)
        self.cursor.clear_lines(lines_req)

    def lines_required(self, tree, count=0):
        """Calculate number of lines required to draw ``tree``"""
        if all([
            isinstance(tree, dict),
            type(tree) != BarDescriptor
        ]):
            return sum(self.lines_required(v, count=count)
                       for v in tree.values()) + 2
        elif isinstance(tree, BarDescriptor):
            if tree.get("kwargs", {}).get("title_pos") in ["left", "right"]:
                return 1
            else:
                return 2

    ###################
    # Private Methods #
    ###################

    def _calculate_values(self, tree, bar_d):
        """Calculate values for drawing bars of non-leafs in ``tree``

        Recurses through ``tree``, replaces ``dict``s with
            ``(BarDescriptor, dict)`` so ``ProgressTree._draw`` can use
            the ``BarDescriptor``s to draw the tree
        """
        if all([
            isinstance(tree, dict),
            type(tree) != BarDescriptor
        ]):
            # Calculate value and max_value
            max_val = 0
            value = 0
            for k in tree:
                # Get descriptor by recursing
                bar_desc = self._calculate_values(tree[k], bar_d)
                # Reassign to tuple of (new descriptor, tree below)
                tree[k] = (bar_desc, tree[k])
                value += bar_desc["value"].value
                max_val += bar_desc.get("kwargs", {}).get("max_value", 100)
            # Merge in values from ``bar_d`` before returning descriptor
            kwargs = merge_dicts(
                [bar_d.get("kwargs", {}),
                 dict(max_value=max_val)],
                deepcopy=True
            )
            ret_d = merge_dicts(
                [bar_d,
                 dict(value=Value(floor(value)), kwargs=kwargs)],
                deepcopy=True
            )
            return BarDescriptor(ret_d)
        elif isinstance(tree, BarDescriptor):
            return tree
        else:
            raise TypeError("Unexpected type {}".format(type(tree)))

    def _draw(self, tree, indent=0):
        """Recurse through ``tree`` and draw all nodes"""
        if all([
            isinstance(tree, dict),
            type(tree) != BarDescriptor
        ]):
            for k, v in sorted(tree.items()):
                bar_desc, subdict = v[0], v[1]

                args = [self.cursor.term] + bar_desc.get("args", [])
                if indent == 0:
                    kwargs = dict(title_pos="left", indent=indent, title=k, num_rep="percentage",
                                  filled_color=1, widgets=[ETA(), FileTransferSpeed()])
                else:
                    kwargs = dict(title_pos="left", indent=indent, title=k, num_rep="percentage",
                                  widgets=[ETA(), FileTransferSpeed()])
                kwargs.update(bar_desc.get("kwargs", {}))

                b = Bar(*args, **kwargs)
                b.draw(value=bar_desc["value"].value, flush=False)

                self._draw(subdict, indent=indent + self.indent)
