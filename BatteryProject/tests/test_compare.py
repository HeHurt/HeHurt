"""Smoke tests for src/compare.py — label matching helpers (no PyBaMM)."""

import unittest

from src.compare import _auto_match, _match_condition_filter, _normalize


class NormalizeTests(unittest.TestCase):
    def test_normalize_handles_degree_variants_and_spaces(self):
        self.assertEqual(_normalize(" 25℃ 0.5P "), "25°c0.5p")
        self.assertEqual(_normalize("25°C 0.5P"), "25°c0.5p")


class MatchConditionFilterTests(unittest.TestCase):
    def test_none_filter_passes_all(self):
        self.assertTrue(_match_condition_filter("25°C 0.5P", None))

    def test_string_temperature_match(self):
        self.assertTrue(_match_condition_filter("25°C 0.5P", "25°C"))
        self.assertFalse(_match_condition_filter("45°C 0.5P", "25°C"))

    def test_and_across_categories(self):
        # Temperature AND rate must both match
        self.assertTrue(_match_condition_filter("25°C 0.5P", ["25°C", "0.5P"]))
        self.assertFalse(_match_condition_filter("25°C 1.0P", ["25°C", "0.5P"]))

    def test_or_within_same_category(self):
        # Two temperatures: OR
        self.assertTrue(_match_condition_filter("25°C 0.5P", ["25°C", "45°C"]))
        self.assertTrue(_match_condition_filter("45°C 0.5P", ["25°C", "45°C"]))
        self.assertFalse(_match_condition_filter("35°C 0.5P", ["25°C", "45°C"]))


class AutoMatchTests(unittest.TestCase):
    def test_matches_on_temperature_and_rate(self):
        sim_labels = ["25°C 0.5P sim", "45°C 1.0P sim"]
        exp_data = [
            {"label": "exp_45°C_1.0P"},
            {"label": "exp_25°C_0.5P"},
        ]
        pairs = _auto_match(sim_labels, exp_data)
        # 期待两对
        self.assertEqual(len(pairs), 2)
        # 验证每个仿真都配到了正确的实验（按温度+倍率）
        for si, ei in pairs:
            sim_lbl = sim_labels[si]
            exp_lbl = exp_data[ei]["label"]
            # 仿真的温度关键词应出现在配对的实验标签中
            for token in ["25°C", "45°C"]:
                if token in sim_lbl:
                    self.assertIn(token, exp_lbl)

    def test_unmatched_returns_empty(self):
        # 完全不同温度倍率，无任何重叠 token
        sim_labels = ["only-text"]
        exp_data = [{"label": "completely-different"}]
        pairs = _auto_match(sim_labels, exp_data)
        self.assertEqual(pairs, [])

    def test_filter_applied(self):
        sim_labels = ["25°C 0.5P", "45°C 0.5P"]
        exp_data = [{"label": "25°C 0.5P"}, {"label": "45°C 0.5P"}]
        pairs = _auto_match(sim_labels, exp_data, filter_conditions="25°C")
        # 仅 25°C 的对应被保留
        self.assertEqual(len(pairs), 1)
        si, ei = pairs[0]
        self.assertIn("25°C", sim_labels[si])
        self.assertIn("25°C", exp_data[ei]["label"])


if __name__ == "__main__":
    unittest.main()
