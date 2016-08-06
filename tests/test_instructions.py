from logging import getLogger, Handler, DEBUG
import unittest


from conda import exceptions
from conda import instructions
from conda.instructions import execute_instructions, commands, pretty_label, new_plan
from collections import OrderedDict

def test_expected_operation_order():
    """Ensure expected order of operations"""
    expected = (
        instructions.FETCH,
        instructions.EXTRACT,
        instructions.UNLINK,
        instructions.LINK,
        instructions.SYMLINK_CONDA,
        instructions.RM_EXTRACTED,
        instructions.RM_FETCHED,
    )
    assert expected == instructions.action_codes


class TestHandler(Handler):
    def __init__(self):
        Handler.__init__(self)
        self.setLevel(DEBUG)
        self.records = []

    def handle(self, record):
        self.records.append((record.name, record.msg))


class TestExecutePlan(unittest.TestCase):

    def test_invalid_instruction(self):
        index = {'This is an index': True}

        plan = [('DOES_NOT_EXIST', ())]

        with self.assertRaises(exceptions.InvalidInstruction):
            execute_instructions(plan, index, verbose=False)

    def test_simple_instruction(self):

        index = {'This is an index': True}

        def simple_cmd(state, arg):
            simple_cmd.called = True
            simple_cmd.call_args = (arg,)

        commands['SIMPLE'] = simple_cmd

        plan = [('SIMPLE', ('arg1',))]

        execute_instructions(plan, index, verbose=False)

        self.assertTrue(simple_cmd.called)
        self.assertTrue(simple_cmd.call_args, ('arg1',))

    def test_state(self):

        index = {'This is an index': True}

        def simple_cmd(state, arg):
            expect, x = arg
            state.setdefault('x', 1)
            self.assertEqual(state['x'], expect)
            state['x'] = x
            simple_cmd.called = True

        commands['SIMPLE'] = simple_cmd

        plan = [('SIMPLE', (1, 5)),
                ('SIMPLE', (5, None)),
                ]

        execute_instructions(plan, index, verbose=False)
        self.assertTrue(simple_cmd.called)

    def test_new_plan(self):

        plan = [('SIMPLE', (1, 5)),
                ('SIMPLE', (10, 11)),
                ('HARD', (10, 11)),
                ('HARD', (21, 22)),
                ]

        res = new_plan(plan)
        correct = OrderedDict()
        correct['SIMPLE'] = [(1,5), (10, 11)]
        correct['HARD'] = [(10, 11), (21, 22)]
        self.assertEquals(res, correct)


class TestLabel(unittest.TestCase):

    def test_label(self):
        general = "conda update conda"
        args = []
        for i in range(30):
            arg = "".join(["*"] * i)
            args.append(arg)

        res = pretty_label(general, args)
        length = len(res[general])
        for val in res:
            self.assertEquals(length, len(res[val]))


if __name__ == '__main__':
    unittest.main()
