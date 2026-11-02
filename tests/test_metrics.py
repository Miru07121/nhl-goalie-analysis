"""Synthetic denominator tests plus the bundled season regression."""
import unittest
import pandas as pd
from analyze import ROOT, calculate_metrics, threshold_sensitivity


class GoalieTests(unittest.TestCase):
    def setUp(self):
        self.raw = pd.DataFrame({
            'playerId': [1, 2, 3], 'name': ['A', 'B', 'C'],
            'season': 2024, 'situation': 'all',
            'icetime': [60000, 59940, 0], 'xGoals': [50.0, 40.0, 0.0],
            'goals': [40, 35, 0], 'ongoal': [500, 400, 0]})

    def test_rates_and_zero_exposure(self):
        result = calculate_metrics(self.raw).set_index('name')
        self.assertEqual(set(result.index), {'A', 'B'})
        self.assertEqual(result.loc['A', 'gsax'], 10)
        self.assertAlmostEqual(result.loc['A', 'gsax_per60'], .6)
        self.assertAlmostEqual(result.loc['A', 'save_pct'], .92)
        self.assertAlmostEqual(result.loc['A', 'gaa'], 2.4)
        self.assertNotIn('gsax', self.raw)

    def test_threshold_boundary_and_empty_cohort(self):
        result = threshold_sensitivity(calculate_metrics(self.raw), (1000, 2000))
        self.assertEqual(result.goalies.tolist(), [1, 0])
        self.assertEqual(result.iloc[0].rate_leader, 'A')
        self.assertTrue(pd.isna(result.iloc[1].rate_leader))
        self.assertTrue(pd.isna(result.iloc[1].leader_gsax_per60))

    def test_invalid_values(self):
        for column, value in [('icetime', float('inf')), ('xGoals', -1),
                              ('goals', 501), ('ongoal', float('inf'))]:
            with self.subTest(column=column, value=value):
                raw = self.raw.copy()
                raw[column] = raw[column].astype(float)
                raw.loc[0, column] = value
                with self.assertRaises(ValueError):
                    calculate_metrics(raw)

    def test_duplicate_id(self):
        self.raw.loc[1, 'playerId'] = 1
        with self.assertRaises(ValueError):
            calculate_metrics(self.raw)

    def test_situation_filter_prevents_double_counting(self):
        raw = pd.concat([self.raw, self.raw.assign(situation='5on5')])
        self.assertEqual(len(calculate_metrics(raw)), 2)

    def test_published_snapshot(self):
        metrics = calculate_metrics(pd.read_csv(ROOT / 'data/goalies_2024.csv'))
        eligible = metrics[metrics.minutes >= 1000]
        self.assertEqual(len(eligible), 62)
        self.assertEqual(eligible.loc[eligible.gsax.idxmax(), 'name'], 'Connor Hellebuyck')
        self.assertAlmostEqual(eligible.gsax.max(), 39.59, places=2)
        self.assertEqual(eligible.loc[eligible.gsax_per60.idxmax(), 'name'], 'Anthony Stolarz')


if __name__ == '__main__':
    unittest.main()
