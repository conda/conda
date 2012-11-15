import unittest

from conda.naming import *

class test_naming(unittest.TestCase):

    def test_split_spec_string(self):
        self.assertEqual(
            split_spec_string('python 2.7'), 
            ('python', '2.7')
        )

        # test when name has numbers in it
        self.assertEqual(
            split_spec_string('python111 2.7.1'),
            ('python111', '2.7.1')
        )

    def test_split_canonical_name(self):
        self.assertEqual(
            split_canonical_name('anaconda-1.1-np17py27_ce0'),
            ('anaconda', '1.1', 'np17py27_ce0')
        )

        # test when name has numbers in it
        self.assertEqual(
            split_canonical_name('anac0nd4-1.1.7-np17py27_ce0anac0nd4'),
            ('anac0nd4', '1.1.7', 'np17py27_ce0anac0nd4')
        )

    def test_get_canonical_name(self):
        self.assertEqual(
            get_canonical_name('anaconda-1.1-np17py27_ce0.tar.bz2'),
            'anaconda-1.1-np17py27_ce0'
        )

        # test when name has tar or bz2 in it
        self.assertEqual(
            get_canonical_name('target-1.1-nptbz2118.tar.bz2'),
            'target-1.1-nptbz2118'
        )

    def test_parse_package_filename(self):
        self.assertEqual(
            parse_package_filename('anaconda-1.1-np17py27_ce0.tar.bz2'),
            ('anaconda', '1.1', 'np17py27_ce0')
        )

        # test when name has numbers in it and tar and bz2
        self.assertEqual(parse_package_filename
            ('anac0nd4-1.1.7-np17py27_ce0tarbz2.tar.bz2'),
            ('anac0nd4', '1.1.7', 'np17py27_ce0tarbz2')
        )



if __name__ == '__main__':
    unittest.main()
