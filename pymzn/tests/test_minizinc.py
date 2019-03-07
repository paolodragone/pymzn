import re
import os
import unittest

from textwrap import dedent
from tempfile import NamedTemporaryFile

from pymzn import minizinc, mzn2fzn, gecode, cbc, MiniZincError


def _save_as_temp_file(content, suffix):
    with NamedTemporaryFile(
        prefix='pymzn_', suffix=suffix, mode='w', delete=False
    ) as f:
        f.write(content)
        file_name = f.name
    return file_name


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
    data_dict_2 = {'capacity': 20}

    data3 = '\n'.join([data1, data2])
    data_dict_3 = {
        'N': 5, 'profit': [10, 3, 9, 4, 8], 'size': [14, 4, 10, 6, 9],
        'capacity': 20
    }

    def test_mzn2fzn(self):

        # Check that TypeError is raised if anything but a string
        # is supplied to the mzn2fzn function
        self.assertRaises(TypeError, mzn2fzn, 0)
        self.assertRaises(TypeError, mzn2fzn, {1, 2, 3})

        # Use temporary files for model and data
        mzn_file = _save_as_temp_file(self.model, '.mzn')
        dzn_file_1 = _save_as_temp_file(self.data1, '.dzn')
        dzn_file_2 = _save_as_temp_file(self.data2, '.dzn')
        dzn_file_3 = _save_as_temp_file(self.data3, '.dzn')

        # Check that MiniZincError is raised if no data is supplied
        self.assertRaises(MiniZincError, mzn2fzn, mzn_file)

        # Check that MiniZincError is raised if not all data needed is supplied
        self.assertRaises(MiniZincError, mzn2fzn, mzn_file, dzn_file_1)
        self.assertRaises(MiniZincError, mzn2fzn, mzn_file, dzn_file_2)

        # Check that files returned by mzn2fzn exist and they are not empty
        fzn_file, ozn_file = mzn2fzn(
            mzn_file, dzn_file_1, data=self.data_dict_2
        )
        self.assertTrue(os.path.isfile(fzn_file))
        self.assertTrue(os.path.isfile(ozn_file))

        fzn_base = os.path.splitext(fzn_file)[0]
        mzn_file_tmp = fzn_base + '.mzn'
        self.assertTrue(os.path.isfile(mzn_file_tmp))

        with open(mzn_file_tmp) as f:
            self.assertNotEqual(f.read(), '')
        with open(fzn_file) as f:
            self.assertNotEqual(f.read(), '')
        with open(ozn_file) as f:
            self.assertNotEqual(f.read(), '')

        os.remove(mzn_file_tmp)
        os.remove(fzn_file)
        os.remove(ozn_file)

        # Check that no_ozn works
        fzn_file, ozn_file = mzn2fzn(mzn_file, dzn_file_3, no_ozn=True)
        self.assertTrue(os.path.isfile(fzn_file))

        fzn_base = os.path.splitext(fzn_file)[0]
        mzn_file_tmp = fzn_base + '.mzn'
        self.assertTrue(os.path.isfile(mzn_file_tmp))

        self.assertEqual(ozn_file, None)
        os.remove(mzn_file_tmp)
        os.remove(fzn_file)

        # Check that keep works
        fzn_file, ozn_file = mzn2fzn(
            mzn_file, data=self.data_dict_3, keep=True
        )
        fzn_base = os.path.splitext(fzn_file)[0]
        mzn_file_tmp = fzn_base + '.mzn'
        dzn_file = fzn_base + '_data.dzn'
        self.assertTrue(os.path.isfile(mzn_file_tmp))
        self.assertTrue(os.path.isfile(dzn_file))

        with open(dzn_file) as f:
            self.assertNotEqual(f.read(), '')

        os.remove(mzn_file_tmp)
        os.remove(fzn_file)
        os.remove(ozn_file)
        os.remove(dzn_file)

        os.remove(mzn_file)

    def test_minizinc(self):
        out = minizinc(self.model, data=self.data_dict_3)
        self.assertEqual(list(out), [{'x': {3, 5}}])


class MinizincTestCalls(unittest.TestCase):

    # check that cbc and gecode solver work with diferent combinations
    # of model and data

    model = dedent('''\
        include "globals.mzn";

        array[1 .. 5] of var 1 .. 5: x;

        constraint all_different(x);
        constraint x[1] > x[2];
        constraint x[2] > x[3];
        constraint x[3] > x[4];
        constraint x[3] > x[5];

        int: k;
        constraint x[5] = k;

        solve maximize x[4]*x[1];
    ''')

    data = {'k': 2}
    solution = [{'x': [5, 4, 3, 1, 2]}]

    # test with data as object
    def _test_data_obj(self, solver):
        out = minizinc(self.model, solver=solver, data=self.data)
        self.assertEqual(list(out), self.solution)

    def test_data_obj_gecode(self):
        self._test_data_obj(gecode)

    def test_data_obj_cbc(self):
        self._test_data_obj(cbc)

    # test with data as string
    def _test_data_str(self, solver):
        out = minizinc(solver=solver, mzn=self.model, data='k=2;')
        self.assertEqual(list(out), self.solution)

    def test_data_str_gecode(self):
        self._test_data_str(gecode)

    def test_data_str_cbc(self):
        self._test_data_str(cbc)

    # test with model as file
    def _test_model_file(self, solver):
        mzn_file = _save_as_temp_file(self.model + '\nk=2;', '.mzn')
        out = minizinc(mzn_file, solver=solver)
        self.assertEqual(list(out), self.solution)
        os.remove(mzn_file)

    def test_model_file_gecode(self):
        self._test_model_file(gecode)

    def test_model_file_cbc(self):
        self._test_model_file(cbc)

    # test with model and data as file
    def _test_model_data_file(self, solver):
        mzn_file = _save_as_temp_file(self.model, '.mzn')
        dzn_file = _save_as_temp_file('k=2;', '.dzn')
        out = minizinc(mzn_file, dzn_file, solver=solver)
        self.assertEqual(list(out), self.solution)
        os.remove(mzn_file)
        os.remove(dzn_file)

    def test_model_data_file_gecode(self):
        self._test_model_data_file(gecode)

    def test_model_data_file_cbc(self):
        self._test_model_data_file(cbc)


class MinizincTestAllSolutions(unittest.TestCase):

    # check that gecode solver returns all solutions
    # this does not work with cbc, we get:
    # WARNING. --all-solutions for SAT problems not implemented.
    # we get only one solution in that case

    model  = dedent('''
        include "globals.mzn";
        array[1 .. 5] of var 1 .. 5: x;
        constraint all_different(x);
        solve satisfy;
    ''')

    def test_gecode(self):
        out = minizinc(self.model, solver=gecode, all_solutions=True)
        self.assertEqual(len(out), 120)

