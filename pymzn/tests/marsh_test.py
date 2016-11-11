import re
import pymzn
import unittest


class MarshTest(unittest.TestCase):

    def test_dzn_value(self):

        def _unwrap(s):
            return re.sub('\s+', ' ', s)

        def _dzn_value(val):
            return _unwrap(pymzn.dzn_value(val))

        self.assertEqual(_dzn_value(1), '1')
        self.assertEqual(_dzn_value(-1), '-1')
        self.assertEqual(_dzn_value(1.0), '1.0')
        self.assertEqual(_dzn_value(-1.0), '-1.0')
        self.assertEqual(_dzn_value(True), 'true')
        self.assertEqual(_dzn_value(False), 'false')
        self.assertEqual(_dzn_value(set()), '{}')
        self.assertEqual(_dzn_value({1, 2, 3}), '1..3')
        self.assertEqual(_dzn_value({1, 3}), '{1, 3}')
        self.assertEqual(_dzn_value({}), 'array1d({}, [])')
        self.assertEqual(_dzn_value([]), 'array1d({}, [])')
        self.assertEqual(_dzn_value([1, 3]), 'array1d(1..2, [1, 3])')
        self.assertEqual(_dzn_value({1: 1, 2: 3}), 'array1d(1..2, [1, 3])')
        self.assertEqual(_dzn_value([[1, 2], [3, 4]]),
                         'array2d(1..2, 1..2, [1, 2, 3, 4])')
        self.assertEqual(_dzn_value([[1, 2, 3], [4, 5, 6]]),
                         'array2d(1..2, 1..3, [1, 2, 3, 4, 5, 6])')
        self.assertEqual(_dzn_value({1: [1, 2, 3], 2: [4, 5, 6]}),
                         'array2d(1..2, 1..3, [1, 2, 3, 4, 5, 6])')
        self.assertEqual(_dzn_value({1: {1: 1, 2: 2, 3: 3}, 2: [4, 5, 6]}),
                         'array2d(1..2, 1..3, [1, 2, 3, 4, 5, 6])')
        self.assertEqual(_dzn_value({1: {1: 1, 2: 2, 3: 3},
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

