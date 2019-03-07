import pymzn
import unittest

from textwrap import dedent

from enum import IntEnum


class EvalTest(unittest.TestCase):

    dzn = dedent('''\
        % This is a comment; with a semicolon
        x1 = 1;x2 = 1.0; x3 = -1.5;
        x4 = {};
        x4a = {  };
        x5 = {1, 3};
        x6 = 1..3;
        x7 = []; x8 =
         array1d({}, []);
        x9 = [1, 2, 3];  % Another comment
        x10 = [{1, 2}, {3, 4}];
        x11 = array1d(1..3,
         [1, 2, 3]);
        x12 = array2d(1..2, 1..3, [1, 2, 3, 4, 5, 6]);x13 = array2d(2..3,
        2..4, [1, 2, 3, 4, 5, 6]);  x14 = array2d(2..3, 1..3, [1, 2, 3, 4,
        5, 6]); x15 = array2d(1..2, 2..4, [1, 2, 3, 4, 5, 6]);
        x16 = [{1}, {2,3}, {}, {4}]; x17 = [ { } ];
        x18=B; x19={A,B};
        P = {A,B, C};\
    ''')

    def test_parse_dzn(self):

        obj = pymzn.dzn2dict(self.dzn)

        for i in range(1, 11):
            self.assertIn('x{}'.format(i), obj)

        self.assertEqual(obj['x1'], 1)
        self.assertEqual(obj['x2'], 1.0)
        self.assertEqual(obj['x3'], -1.5)
        self.assertEqual(obj['x4'], set())
        self.assertEqual(obj['x4a'], set())
        self.assertEqual(obj['x5'], {1, 3})
        self.assertEqual(obj['x6'], pymzn.IntSet(1, 3))
        self.assertEqual(obj['x7'], [])
        self.assertEqual(obj['x8'], [])
        self.assertEqual(obj['x9'], [1, 2, 3])
        self.assertEqual(obj['x10'], [{1, 2}, {3, 4}])
        self.assertEqual(obj['x11'], [1, 2, 3])
        self.assertEqual(obj['x12'], [[1, 2, 3], [4, 5, 6]])
        self.assertEqual(
            obj['x13'], {2: {2: 1, 3: 2, 4: 3}, 3: {2: 4, 3: 5, 4: 6}}
        )
        self.assertEqual(obj['x14'], {2: [1, 2, 3], 3: [4, 5, 6]})
        self.assertEqual(obj['x15'], [{2: 1, 3: 2, 4: 3}, {2: 4, 3: 5, 4: 6}])
        self.assertEqual(obj['x16'], [{1}, {2,3}, set(), {4}])
        self.assertEqual(obj['x17'], [set()])
        self.assertEqual(obj['x18'], 'B')
        self.assertEqual(obj['x19'], set(['A', 'B']))

    def test_parse_dzn_types(self):

        obj = pymzn.dzn2dict(self.dzn, types={
            'x18': {'type': 'int', 'enum_type': 'P'},
            'x19': {'type': 'int', 'set': True, 'enum_type': 'P'},
            'P': {'type': 'int', 'set': True, 'enum_type': 'P'},
        })

        self.assertIsInstance(obj['x18'], IntEnum)
        self.assertEqual(obj['x18'], 2)
        self.assertEqual(type(obj['x18']).__name__, 'P')
        self.assertEqual(obj['x19'], set({1, 2}))

        obj = pymzn.dzn2dict(self.dzn, types={
            'x18': {'type': 'int', 'enum_type': 'P'},
            'x19': {'type': 'int', 'set': True, 'enum_type': 'P'},
        })

        self.assertEqual(obj['x18'], 'B')
        self.assertEqual(obj['x19'], set(['A', 'B']))
        self.assertIsInstance(obj['P'], set)
        self.assertEqual(obj['P'], set(['A', 'B', 'C']))

        # If supply wrong type raise ValueError
        self.assertRaises(
            ValueError, pymzn.dzn2dict, self.dzn,
            types={'x2': {'type': 'int'}}
        )

