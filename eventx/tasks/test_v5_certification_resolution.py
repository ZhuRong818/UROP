"""Synthetic checks for candidate family graph and grouped-t diagnostic."""

import unittest

import numpy as np
from scipy.stats import t

from eventx.tasks.certify_v5_family_graph import components, validate_split_certificate
from eventx.tasks.screen_v5_group_t_candidate import group_interval


class CertificationTests(unittest.TestCase):
    def test_transitive_graph_and_order(self):
        edges = [('a', 'b'), ('c', 'b')]
        self.assertEqual(components('abcd', edges), [['a', 'b', 'c'], ['d']])
        self.assertEqual(components('dcba', edges[::-1]), [['a', 'b', 'c'], ['d']])

    def test_unknown_edge_rejected(self):
        with self.assertRaises(ValueError):
            components('ab', [('a', 'c')])

    def test_split_known_dependency_rejected(self):
        with self.assertRaisesRegex(ValueError, 'must-link'):
            validate_split_certificate('ab', [('a', 'b')], {'a': 'x', 'b': 'y'}, {'a': True, 'b': True})

    def test_boundary_review_required(self):
        result = validate_split_certificate('ab', [('a', 'b')], {'a': 'x', 'b': 'x'}, {'a': True, 'b': False})
        self.assertTrue(result['graph_consistent'])
        self.assertFalse(result['final_family_certified'])
        with self.assertRaises(ValueError):
            validate_split_certificate('ab', [], {'a': 'x'}, {})

    def test_graph_approval_does_not_assert_source_or_statistical_independence(self):
        result = validate_split_certificate('ab', [('a', 'b')], {'a': 'x', 'b': 'x'}, {'a': True, 'b': True})
        self.assertIn('not source-version admission or statistical independence', result['scope'])

    def test_group_t_formula(self):
        family, day = np.repeat(np.arange(4), 8), np.tile(np.arange(8), 4)
        values = family/10
        lb, ub, used = group_interval(values, family, day)
        half = t.ppf(.975, 3)*np.std([0., .1, .2, .3], ddof=1)/2
        self.assertAlmostEqual(lb, .15-half)
        self.assertAlmostEqual(ub, .15+half)
        self.assertEqual(used, .25)

    def test_missing_diagonal_group_refused(self):
        with self.assertRaisesRegex(ValueError, 'Empty diagonal'):
            group_interval(np.ones(8), np.zeros(8), np.arange(8))


if __name__ == '__main__':
    unittest.main()
