from conda.instructions import execute_instructions, InvaidInstruction, commands
import unittest


class TestExecutePlan(unittest.TestCase):

    def test_invalid_instruction(self):
        index = {'This is an index': True}

        plan = [('DOES_NOT_EXIST', ())]

        with self.assertRaises(InvaidInstruction):
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

        def simple_cmd(state, expect, x):
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


if __name__ == '__main__':
    unittest.main()
