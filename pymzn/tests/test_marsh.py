from __future__ import absolute_import
import re
import pymzn
import unittest


class MarshTest(unittest.TestCase):

    def test_dzn_value(self):

        def _unwrap(s):
            return re.sub(u'\s+', u' ', s)

        def _dzn_value(val):
            return _unwrap(pymzn.val2dzn(val))

        self.assertEqual(_dzn_value(1), u'1')
        self.assertEqual(_dzn_value(-1), u'-1')
        self.assertEqual(_dzn_value(1.0), u'1.0')
        self.assertEqual(_dzn_value(-1.0), u'-1.0')
        self.assertEqual(_dzn_value(True), u'true')
        self.assertEqual(_dzn_value(False), u'false')
        self.assertEqual(_dzn_value(set()), u'{}')
        self.assertEqual(_dzn_value(set([1, 2, 3])), u'1..3')
        self.assertEqual(_dzn_value(set([1, 3])), u'{1, 3}')
        self.assertEqual(_dzn_value({}), u'array1d({}, [])')
        self.assertEqual(_dzn_value([]), u'array1d({}, [])')
        self.assertEqual(_dzn_value([1, 3]), u'array1d(1..2, [1, 3])')
        self.assertEqual(_dzn_value({1: 1, 2: 3}), u'array1d(1..2, [1, 3])')
        self.assertEqual(_dzn_value([[1, 2], [3, 4]]),
                         u'array2d(1..2, 1..2, [1, 2, 3, 4])')
        self.assertEqual(_dzn_value([[1, 2, 3], [4, 5, 6]]),
                         u'array2d(1..2, 1..3, [1, 2, 3, 4, 5, 6])')
        self.assertEqual(_dzn_value({1: [1, 2, 3], 2: [4, 5, 6]}),
                         u'array2d(1..2, 1..3, [1, 2, 3, 4, 5, 6])')
        self.assertEqual(_dzn_value({1: {1: 1, 2: 2, 3: 3}, 2: [4, 5, 6]}),
                         u'array2d(1..2, 1..3, [1, 2, 3, 4, 5, 6])')
        self.assertEqual(_dzn_value({1: {1: 1, 2: 2, 3: 3},
                                     2: {1: 4, 2: 5, 3: 6}}),
                         u'array2d(1..2, 1..3, [1, 2, 3, 4, 5, 6])')

    def test_raises_dzn_value(self):
        class _Dummy(object):
            pass
        self.assertRaises(TypeError, pymzn.val2dzn, _Dummy())
        self.assertRaises(ValueError, pymzn.val2dzn, [[[[[[[1]]]]]]])
        self.assertRaises(ValueError, pymzn.val2dzn, {u'1': 1, u'2': 2})
        self.assertRaises(ValueError, pymzn.val2dzn, {0.1: 1, 0.2: 2})

    def test_dzn(self):
        dzn = pymzn.dict2dzn({u'x': 1, u'y': 2})
        self.assertIn(u'x = 1;', dzn)
        self.assertIn(u'y = 2;', dzn)

    def test_rebase_array(self):
        self.assertEqual(pymzn.rebase_array({2: 1, 3: 2, 4: 3}), [1, 2, 3])

