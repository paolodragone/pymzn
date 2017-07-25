from __future__ import absolute_import
import pymzn
import unittest

from textwrap import dedent


class EvalTest(unittest.TestCase):

    def test_eval_dzn(self):
        dzn = dedent(u'''\
            x1 = 1;x2 = 1.0; x3 = -1.5;
            x4 = {};
            x5 = {1, 3};
            x6 = 1..3;
            x7 = []; x8 =
             array1d({}, []);
            x9 = [1, 2, 3];
            x10 = [{1, 2}, {3, 4}];
            x11 = array1d(1..3,
             [1, 2, 3]);
            x12 = array2d(1..2, 1..3, [1, 2, 3, 4, 5, 6]);x13 = array2d(2..3,
            2..4, [1, 2, 3, 4, 5, 6]);  x14 = array2d(2..3, 1..3, [1, 2, 3, 4,
            5, 6]); x15 = array2d(1..2, 2..4, [1, 2, 3, 4, 5, 6])
            ;''')

        obj = pymzn.dzn2dict(dzn)
        for i in xrange(1, 11):
            self.assertIn(u'x{}'.format(i), obj)
        self.assertEqual(obj[u'x1'], 1)
        self.assertEqual(obj[u'x2'], 1.0)
        self.assertEqual(obj[u'x3'], -1.5)
        self.assertEqual(obj[u'x4'], set())
        self.assertEqual(obj[u'x5'], set([1, 3]))
        self.assertEqual(obj[u'x6'], set([1, 2, 3]))
        self.assertEqual(obj[u'x7'], [])
        self.assertEqual(obj[u'x8'], [])
        self.assertEqual(obj[u'x9'], [1, 2, 3])
        self.assertEqual(obj[u'x10'], [set([1, 2]), set([3, 4])])
        self.assertEqual(obj[u'x11'], [1, 2, 3])
        self.assertEqual(obj[u'x12'], [[1, 2, 3], [4, 5, 6]])
        self.assertEqual(obj[u'x13'], {2: {2: 1, 3: 2, 4: 3},
                                      3: {2: 4, 3: 5, 4: 6}})
        self.assertEqual(obj[u'x14'], {2: [1, 2, 3], 3: [4, 5, 6]})
        self.assertEqual(obj[u'x15'], [{2: 1, 3: 2, 4: 3}, {2: 4, 3: 5, 4: 6}])

