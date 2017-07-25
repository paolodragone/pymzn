from __future__ import absolute_import
import re
import os
import pymzn
import os.path
import unittest
from tempfile import NamedTemporaryFile

from textwrap import dedent


class MinizincTest(unittest.TestCase):

    model = dedent(u'''\
        int: N;
        set of int: OBJ = 1..N;
        int: capacity;
        array[OBJ] of int: profit;
        array[OBJ] of int: size;

        var set of OBJ: x;
        constraint sum(i in x)(size[i]) <= capacity;
        var int: obj = sum(i in x)(profit[i]);
        solve maximize obj;
        ''')

    data1 = dedent(u'''\
        N = 5;
        profit = [10, 3, 9, 4, 8];
        size = [14, 4, 10, 6, 9];
        ''')
    data2 = u'capacity = 20;'
    data3 = u'\n'.join([data1, data2])

    def test_mzn2fzn(self):

        self.assertRaises(TypeError, pymzn.mzn2fzn, 0)
        self.assertRaises(TypeError, pymzn.mzn2fzn, set([1, 2, 3]))

        mzn_file = NamedTemporaryFile(prefix=u'pymzn_', suffix=u'.mzn', mode=u'w',
                                      delete=False)
        mzn_file.write(self.model)
        mzn_file.close()
        mzn = mzn_file.name
        mzn_base = os.path.splitext(mzn)[0]

        self.assertRaises(RuntimeError, pymzn.mzn2fzn, mzn)

        dzn_file = NamedTemporaryFile(prefix=u'pymzn_', suffix=u'.dzn', mode=u'w',
                                      buffering=1)
        dzn_file.write(self.data1)
        dzn = dzn_file.name
        self.assertRaises(RuntimeError, pymzn.mzn2fzn, mzn, dzn)
        dzn_file.close()

        dzn_file = NamedTemporaryFile(prefix=u'pymzn_', suffix=u'.dzn', mode=u'w',
                                      buffering=1)
        dzn_file.write(self.data2)
        dzn = dzn_file.name
        self.assertRaises(RuntimeError, pymzn.mzn2fzn, mzn, dzn)
        dzn_file.close()

        dzn_file = NamedTemporaryFile(prefix=u'pymzn_', suffix=u'.dzn', mode=u'w',
                                      buffering=1)
        dzn_file.write(self.data1)
        dzn_file.flush()
        dzn = dzn_file.name
        fzn = mzn_base + u'.fzn'
        ozn = mzn_base + u'.ozn'
        self.assertEqual(pymzn.mzn2fzn(mzn, dzn, data={u'capacity': 20}),
                         (fzn, ozn))
        dzn_file.close()
        self.assertTrue(os.path.isfile(fzn))
        self.assertTrue(os.path.isfile(ozn))
        os.remove(fzn)
        os.remove(ozn)

        dzn_file = NamedTemporaryFile(prefix=u'pymzn_', suffix=u'.dzn', mode=u'w',
                                      buffering=1)
        dzn_file.write(self.data3)
        dzn_file.flush()
        dzn = dzn_file.name
        fzn = mzn_base + u'.fzn'
        ozn = mzn_base + u'.ozn'
        self.assertEqual(pymzn.mzn2fzn(mzn, dzn), (fzn, ozn))
        dzn_file.close()
        self.assertTrue(os.path.isfile(fzn))
        self.assertTrue(os.path.isfile(ozn))
        os.remove(fzn)
        os.remove(ozn)

        dzn_file = NamedTemporaryFile(prefix=u'pymzn_', suffix=u'.dzn', mode=u'w',
                                      buffering=1)
        dzn_file.write(self.data3)
        dzn = dzn_file.name
        fzn = mzn_base + u'.fzn'
        ozn = mzn_base + u'.ozn'
        self.assertEqual(pymzn.mzn2fzn(mzn, dzn, no_ozn=True), (fzn, None))
        dzn_file.close()
        self.assertTrue(os.path.isfile(fzn))
        self.assertFalse(os.path.isfile(ozn))
        os.remove(fzn)

        fzn, ozn = pymzn.mzn2fzn(mzn, data={u'N': 5, u'profit': [10, 3, 9, 4, 8],
                                 u'size': [14, 4, 10, 6, 9], u'capacity': 20},
                                 keep_data=True)
        dzn = mzn_base + u'_data.dzn'
        self.assertEqual(fzn, mzn_base + u'.fzn')
        self.assertEqual(ozn, mzn_base + u'.ozn')
        self.assertTrue(os.path.isfile(dzn))
        os.remove(fzn)
        os.remove(ozn)
        os.remove(dzn)

        os.remove(mzn)


    def test_minizinc(self):
        out = pymzn.minizinc(self.model,
                             data={u'N': 5, u'profit': [10, 3, 9, 4, 8],
                                   u'size': [14, 4, 10, 6, 9],
                                   u'capacity': 20})
        self.assertEqual(list(out), [{u'x': set([3, 5])}])

