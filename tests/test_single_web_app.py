import json
import unittest

from bot_single import _parse_web_app_order
from bouquet_generator import resolve_premade_path


class SingleWebAppOrderTests(unittest.TestCase):
    def test_parse_valid_order(self):
        raw = json.dumps({
            "version": 1,
            "student_id": "HPS-ISS9003",
            "flower_id": 3,
            "quantity": 5,
        })
        student_id, flower_id, quantity = _parse_web_app_order(raw)
        self.assertEqual(student_id, "HPS-ISS9003")
        self.assertEqual(flower_id, 3)
        self.assertEqual(quantity, 5)

    def test_parse_rejects_invalid_quantity(self):
        raw = json.dumps({
            "version": 1,
            "student_id": "HPS-ISS9003",
            "flower_id": 1,
            "quantity": 11,
        })
        with self.assertRaises(ValueError):
            _parse_web_app_order(raw)

    def test_resolve_premade_path_returns_existing_file(self):
        import os
        # sunflower = flower_id 9; uses IMG-named files
        path = resolve_premade_path("sunflower", 10)
        self.assertTrue(os.path.isfile(path), f"Expected file to exist: {path}")
        # rose = flower_id 1; uses numeric names
        path_rose = resolve_premade_path("rose", 5)
        self.assertTrue(os.path.isfile(path_rose))

    def test_parse_rejects_missing_student_id(self):
        raw = json.dumps({
            "version": 1,
            "student_id": "   ",
            "flower_id": 1,
            "quantity": 3,
        })
        with self.assertRaises(ValueError):
            _parse_web_app_order(raw)


if __name__ == "__main__":
    unittest.main()
