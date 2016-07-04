import shutil
import tempfile
import unittest

from pymzn import minizinc
from pymzn.bin import BinaryRuntimeError


class MiniZincTest(unittest.TestCase):

    def test_minizinc_exists(self):
        self.assertIsNotNone(shutil.which('mzn2fzn'), 'mzn2fzn not found.')
        self.assertIsNotNone(shutil.which('solns2out'), 'solns2out not found.')

    def test_minizinc_simple(self):
        p = ('var 0..10: x;\n'
             'solve maximize x;\n')

        with tempfile.NamedTemporaryFile(mode='w+t', suffix='.mzn') as f:
            f.write(p)
            f.file.flush()
            sol = minizinc(f.name)
        self.assertEqual(sol, [{'x': 10}])

    def test_minizinc_except(self):
        p = 'var 0..10: x;\n'
        with tempfile.NamedTemporaryFile(mode='w+t', suffix='.mzn') as f:
            f.write(p)
            f.file.flush()
            self.assertRaises(BinaryRuntimeError, minizinc, f.name)


if __name__ == '__main__':
    unittest.main()
