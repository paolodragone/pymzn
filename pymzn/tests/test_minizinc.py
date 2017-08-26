import re
import os
import pymzn
import os.path
import unittest
from tempfile import NamedTemporaryFile

from textwrap import dedent


class MinizincTest(unittest.TestCase):

    model = dedent('''\
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

    data1 = dedent('''\
        N = 5;
        profit = [10, 3, 9, 4, 8];
        size = [14, 4, 10, 6, 9];
        ''')
    data2 = 'capacity = 20;'
    data3 = '\n'.join([data1, data2])

    def test_mzn2fzn(self):

        self.assertRaises(TypeError, pymzn.mzn2fzn, 0)
        self.assertRaises(TypeError, pymzn.mzn2fzn, {1, 2, 3})

        mzn_file = NamedTemporaryFile(prefix='pymzn_', suffix='.mzn', mode='w',
                                      delete=False)
        mzn_file.write(self.model)
        mzn_file.close()
        mzn = mzn_file.name
        mzn_base = os.path.splitext(mzn)[0]

        self.assertRaises(RuntimeError, pymzn.mzn2fzn, mzn)

        dzn_file = NamedTemporaryFile(prefix='pymzn_', suffix='.dzn', mode='w',
                                      buffering=1)
        dzn_file.write(self.data1)
        dzn = dzn_file.name
        self.assertRaises(RuntimeError, pymzn.mzn2fzn, mzn, dzn)
        dzn_file.close()

        dzn_file = NamedTemporaryFile(prefix='pymzn_', suffix='.dzn', mode='w',
                                      buffering=1)
        dzn_file.write(self.data2)
        dzn = dzn_file.name
        self.assertRaises(RuntimeError, pymzn.mzn2fzn, mzn, dzn)
        dzn_file.close()

        dzn_file = NamedTemporaryFile(prefix='pymzn_', suffix='.dzn', mode='w',
                                      buffering=1)
        dzn_file.write(self.data1)
        dzn_file.flush()
        dzn = dzn_file.name
        fzn = mzn_base + '.fzn'
        ozn = mzn_base + '.ozn'
        self.assertEqual(pymzn.mzn2fzn(mzn, dzn, data={'capacity': 20}),
                         (fzn, ozn))
        dzn_file.close()
        self.assertTrue(os.path.isfile(fzn))
        self.assertTrue(os.path.isfile(ozn))
        os.remove(fzn)
        os.remove(ozn)

        dzn_file = NamedTemporaryFile(prefix='pymzn_', suffix='.dzn', mode='w',
                                      buffering=1)
        dzn_file.write(self.data3)
        dzn_file.flush()
        dzn = dzn_file.name
        fzn = mzn_base + '.fzn'
        ozn = mzn_base + '.ozn'
        self.assertEqual(pymzn.mzn2fzn(mzn, dzn), (fzn, ozn))
        dzn_file.close()
        self.assertTrue(os.path.isfile(fzn))
        self.assertTrue(os.path.isfile(ozn))
        os.remove(fzn)
        os.remove(ozn)

        dzn_file = NamedTemporaryFile(prefix='pymzn_', suffix='.dzn', mode='w',
                                      buffering=1)
        dzn_file.write(self.data3)
        dzn = dzn_file.name
        fzn = mzn_base + '.fzn'
        ozn = mzn_base + '.ozn'
        self.assertEqual(pymzn.mzn2fzn(mzn, dzn, no_ozn=True), (fzn, None))
        dzn_file.close()
        self.assertTrue(os.path.isfile(fzn))
        self.assertFalse(os.path.isfile(ozn))
        os.remove(fzn)

        fzn, ozn = pymzn.mzn2fzn(mzn, data={'N': 5, 'profit': [10, 3, 9, 4, 8],
                                 'size': [14, 4, 10, 6, 9], 'capacity': 20},
                                 keep_data=True)
        dzn = mzn_base + '_data.dzn'
        self.assertEqual(fzn, mzn_base + '.fzn')
        self.assertEqual(ozn, mzn_base + '.ozn')
        self.assertTrue(os.path.isfile(dzn))
        os.remove(fzn)
        os.remove(ozn)
        os.remove(dzn)

        os.remove(mzn)


    def test_minizinc(self):
        out = pymzn.minizinc(self.model,
                             data={'N': 5, 'profit': [10, 3, 9, 4, 8],
                                   'size': [14, 4, 10, 6, 9],
                                   'capacity': 20})
        self.assertEqual(list(out), [{'x': {3, 5}}])

    def test_minizinc2(self):
        # test that the temp file is flushed or closed
        # somehow the file is flushed if there is a \n in the string written
        out = list(pymzn.minizinc("var 1 .. 1: x; solve maximize x;"))
        self.assertEqual(list(out), [{'x': 1}])


class MinizincTestCalls(unittest.TestCase):
    # check that cbc and gecode solver work with diferent combinations
    # of model and data
    model = '''
     include "globals.mzn";
     array[1..5] of var 1 .. 5: x;
     constraint all_different(x);
     constraint x[1]>x[2];
     constraint x[2]>x[3];
     constraint x[3]>x[4];
     constraint x[3]>x[5];
     int: k;
     constraint x[5] = k;
     solve maximize x[4]*x[1];
'''
    data = {'k':2}
    solution = [{'x': [5,4,3,1,2]}]

    # test with data as object
    def _test_data_obj(self, solver):
        out = list(pymzn.minizinc(solver=solver, mzn=self.model, data=self.data))
        self.assertEqual(out, self.solution)

    def test_data_obj_gecode(self):
        self._test_data_obj('gecode')

    def test_data_obj_cbc(self):
        self._test_data_obj('cbc')

    # test with data as string
    def _test_data_str(self, solver):
        out = list(pymzn.minizinc(solver=solver, mzn=self.model, data='k=2;'))
        self.assertEqual(out, self.solution)

    def test_data_str_gecode(self):
        self._test_data_str('gecode')

    def test_data_str_cbc(self):
        self._test_data_str('cbc')


    def save_as_temp_file(self, contents, suffix):
        import tempfile
        f = tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False)
        file_name = f.name
        f.write(contents)
        f.close()
        return file_name

    # test with model as file
    def _test_model_file(self, solver):
        import os
        fn = self.save_as_temp_file(self.model +'\nk=2;', '.mzn')
        out = list(pymzn.minizinc(solver=solver, mzn=fn))
        os.remove(fn)
        self.assertEqual(out, self.solution)

    def test_model_file_gecode(self):
        self._test_model_file('gecode')

    def test_model_file_cbc(self):
        self._test_model_file('cbc')

    # test with model and data as file
    def _test_model_data_file(self, solver):
        import os
        fn = self.save_as_temp_file(self.model, '.mzn')
        dn = self.save_as_temp_file('k=2;', '.dzn')
        out = list(pymzn.minizinc(fn, dn, solver=solver))
        os.remove(fn)
        self.assertEqual(out, self.solution)

    def test_model_data_file_gecode(self):
        self._test_model_data_file('gecode')

    def test_model_data_file_cbc(self):
        self._test_model_data_file('cbc')


class MinizincTestAllSolutions(unittest.TestCase):
    # check that gecode solver returns all solutions
    # this does not work with cbc, we get:
    #  WARNING. --all-solutions for SAT problems not implemented.
    # we get only one solution in that case
    model  = '''
     include "globals.mzn";
     array[1..5] of var 1 .. 5: x;
     constraint all_different(x);
     solve satisfy;
'''
    def test_gecode(self):
        out = list(pymzn.minizinc(solver='gecode', mzn=self.model, all_solutions=True))
        self.assertEqual(len(out), 120)
