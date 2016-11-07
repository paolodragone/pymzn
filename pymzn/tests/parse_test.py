import unittest
import pymzn


class ParseTest(unittest.TestCase):

    def test_parse_dzn(self):
        dzn = ('x1 = 1;'
               'x2 = 1.0; '
               'x3 = -1.5;\n'
               'x4 = {};\n'
               'x5 = {1, 3};\n'
               'x6 = 1..3;\n'
               'x7 = []; '
               'x8 = \n array1d({}, []);\n'
               'x9 = [1, 2, 3];\n'
               'x10 = [{1, 2}, {3, 4}];\n'
               'x11 = array1d(1..3, \n [1, 2, 3]);\n'
               'x12 = array2d(1..2, 1..3, [1, 2, 3, 4, 5, 6]);'
               'x13 = array2d(2..3, \n 2..4, [1, 2, 3, 4, 5, 6]);  '
               'x14 = array2d(2..3, 1..3, [1, 2, 3, 4, 5, 6]);\n'
               'x15 = array2d(1..2, 2..4, [1, 2, 3, 4, 5, 6])\n;'
               )

        parsed = pymzn.parse_dzn(dzn)
        for i in range(1, 11):
            self.assertIn('x{}'.format(i), parsed)
        self.assertEqual(parsed['x1'], 1)
        self.assertEqual(parsed['x2'], 1.0)
        self.assertEqual(parsed['x3'], -1.5)
        self.assertEqual(parsed['x4'], set())
        self.assertEqual(parsed['x5'], {1, 3})
        self.assertEqual(parsed['x6'], {1, 2, 3})
        self.assertEqual(parsed['x7'], [])
        self.assertEqual(parsed['x8'], [])
        self.assertEqual(parsed['x9'], [1, 2, 3])
        self.assertEqual(parsed['x10'], [{1, 2}, {3, 4}])
        self.assertEqual(parsed['x11'], [1, 2, 3])
        self.assertEqual(parsed['x12'], [[1, 2, 3], [4, 5, 6]])
        self.assertEqual(parsed['x13'],
                         {2: {2: 1, 3: 2, 4: 3}, 3: {2: 4, 3: 5, 4: 6}})
        self.assertEqual(parsed['x14'], {2: [1, 2, 3], 3: [4, 5, 6]})
        self.assertEqual(parsed['x15'],
                         [{2: 1, 3: 2, 4: 3}, {2: 4, 3: 5, 4: 6}])


if __name__ == '__main__':
    unittest.main()