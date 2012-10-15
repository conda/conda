import unittest
from conda.requirement import *

class test_requirement(unittest.TestCase):

    # test when packages have dashes and numbers, versions have letters
    def test_init(self):
        example = requirement("python-2.7.1 2.7.1.abc")
        self.assertEqual(
            example.name, 
            "python-2.7.1"
        )
        self.assertEqual(
            example.version, 
            LooseVersion('2.7.1.abc')
        )

class test_requirements_consistent(unittest.TestCase):

    def test_find_inconsistent_requirements(self):
        a, b, c = requirement('python 2.7'), requirement('python 3.1'), requirement('python 2.7.1')
        example = [a,b,c]
        self.assertEqual(
            find_inconsistent_requirements(example),
            set([requirement('python 2.7.1'),
                 requirement('python 3.1'),
                 requirement('python 2.7')])
        )


if __name__ == '__main__':
    unittest.main()