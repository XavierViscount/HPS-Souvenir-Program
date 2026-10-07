import json
import unittest

from bot_mixed import _parse_web_app_order


class MixedWebAppOrderTests(unittest.TestCase):
    def test_parse_individual_order(self):
        raw = json.dumps({
            "version": 1,
            "student_id": "HPS-ISS9003",
            "mode": "individual",
            "flower_ids": [1, 4, 4],
            "arrangement": "fan",
        })

        student_id, flower_ids, arrangement = _parse_web_app_order(raw)

        self.assertEqual(student_id, "HPS-ISS9003")
        self.assertEqual(flower_ids, [1, 4, 4])
        self.assertEqual(arrangement, "fan")

    def test_parse_all_flowers_order(self):
        raw = json.dumps({
            "version": 1,
            "student_id": "HPS-ISS9003",
            "mode": "all",
            "flower_ids": [],
            "arrangement": "balanced",
        })

        _, flower_ids, _ = _parse_web_app_order(raw)

        self.assertEqual(flower_ids, list(range(1, 11)))

    def test_reject_order_with_too_many_flowers(self):
        raw = json.dumps({
            "version": 1,
            "student_id": "HPS-ISS9003",
            "mode": "individual",
            "flower_ids": [1] * 11,
            "arrangement": "balanced",
        })

        with self.assertRaises(ValueError):
            _parse_web_app_order(raw)

    def test_reject_order_with_invalid_mode(self):
        raw = json.dumps({
            "version": 1,
            "student_id": "HPS-ISS9003",
            "mode": [],
            "flower_ids": [1],
            "arrangement": "balanced",
        })

        with self.assertRaises(ValueError):
            _parse_web_app_order(raw)


if __name__ == "__main__":
    unittest.main()