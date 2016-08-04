import unittest
import pymzn
import re

class MarshTest(unittest.TestCase):

    def test_dzn_value(self):
        self.assertEqual(pymzn.dzn_value(1), '1')
        self.assertEqual(pymzn.dzn_value(-1), '-1')
        self.assertEqual(pymzn.dzn_value(1.0), '1.0')
        self.assertEqual(pymzn.dzn_value(-1.0), '-1.0')
        self.assertEqual(pymzn.dzn_value(True), 'true')
        self.assertEqual(pymzn.dzn_value(False), 'false')
        self.assertEqual(pymzn.dzn_value(set()), '{}')
        self.assertEqual(pymzn.dzn_value({1, 2, 3}), '1..3')
        self.assertEqual(pymzn.dzn_value({1, 3}), '{1, 3}')
        self.assertEqual(pymzn.dzn_value({}), 'array1d({}, [])')
        self.assertEqual(pymzn.dzn_value([]), 'array1d({}, [])')

        def arr_value(val):
            arr = pymzn.dzn_value(val)
            arr = re.sub('\s+', ' ', arr)
            return arr

        self.assertEqual(arr_value([1, 3]), 'array1d(1..2, [1, 3])')
        self.assertEqual(arr_value({1: 1, 2: 3}), 'array1d(1..2, [1, 3])')
        self.assertEqual(arr_value([[1, 2], [3, 4]]),
                         'array2d(1..2, 1..2, [1, 2, 3, 4])')
        self.assertEqual(arr_value([[1, 2, 3], [4, 5, 6]]),
                         'array2d(1..2, 1..3, [1, 2, 3, 4, 5, 6])')
        self.assertEqual(arr_value({1: [1, 2, 3], 2: [4, 5, 6]}),
                         'array2d(1..2, 1..3, [1, 2, 3, 4, 5, 6])')
        self.assertEqual(arr_value({1: {1: 1, 2: 2, 3: 3},
                                    2: [4, 5, 6]}),
                         'array2d(1..2, 1..3, [1, 2, 3, 4, 5, 6])')
        self.assertEqual(arr_value({1: {1: 1, 2: 2, 3: 3},
                                    2: {1: 4, 2: 5, 3: 6}}),
                         'array2d(1..2, 1..3, [1, 2, 3, 4, 5, 6])')

    def test_raises_dzn_value(self):
        class _Dummy(object):
            pass
        self.assertRaises(TypeError, pymzn.dzn_value, _Dummy())
        self.assertRaises(ValueError, pymzn.dzn_value, [[[[[[[1]]]]]]])
        self.assertRaises(ValueError, pymzn.dzn_value, {'1': 1, '2': 2})
        self.assertRaises(ValueError, pymzn.dzn_value, {0.1: 1, 0.2: 2})

    def test_dzn(self):
        dzn = pymzn.dzn({'x': 1, 'y': 2})
        self.assertIn('x = 1;', dzn)
        self.assertIn('y = 2;', dzn)

    def test_rebase_array(self):
        self.assertEqual(pymzn.rebase_array({2: 1, 3: 2, 4: 3}), [1, 2, 3])
