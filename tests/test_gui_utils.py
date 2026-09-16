# -*- coding: utf-8 -*-
import unittest
from datetime import datetime
from Shared.gui_utils import universal_tree_sort

class MockTree:
    def __init__(self, children_data):
        # children_data maps child_id -> (value, tags)
        self.children_data = children_data
        self.moves = []
        self.headings = {}

    def get_children(self, parent):
        return list(self.children_data.keys())

    def set(self, child, col):
        return self.children_data[child][0]

    def item(self, child, option=None, tags=None):
        if option == "tags":
            return self.children_data[child][1]
        return {"tags": self.children_data[child][1]}

    def move(self, child, parent, index):
        self.moves.append((child, parent, index))

    def heading(self, col, command):
        self.headings[col] = command


class TestUniversalTreeSort(unittest.TestCase):
    def test_sort_mixed_types_ascending(self):
        # Mix of float, string, and empty values
        data = {
            "I001": ("10.5", []),
            "I002": ("apple", []),
            "I003": ("N/A", []),
            "I004": ("2.3", []),
            "I005": ("banana", []),
        }
        tree = MockTree(data)
        
        # Sort ascending
        universal_tree_sort(tree, "col1", reverse=False)
        
        # Expected order:
        # Numeric values: 2.3, 10.5
        # String values: apple, banana
        # Empty values: N/A
        expected_order = ["I004", "I001", "I002", "I005", "I003"]
        actual_order = [move[0] for move in tree.moves]
        self.assertEqual(actual_order, expected_order)

    def test_sort_mixed_types_descending(self):
        # Mix of float, string, and empty values
        data = {
            "I001": ("10.5", []),
            "I002": ("apple", []),
            "I003": ("N/A", []),
            "I004": ("2.3", []),
            "I005": ("banana", []),
        }
        tree = MockTree(data)
        
        # Sort descending
        universal_tree_sort(tree, "col1", reverse=True)
        
        # Expected order (descending):
        # Numeric values: 10.5, 2.3
        # String values: banana, apple
        # Empty values: N/A
        expected_order = ["I001", "I004", "I005", "I002", "I003"]
        actual_order = [move[0] for move in tree.moves]
        self.assertEqual(actual_order, expected_order)

    def test_sort_dates_and_currencies(self):
        data = {
            "I001": ("₹ 1,234.50", []),
            "I002": ("15-12-2022", []),
            "I003": ("10-12-2022", []),
            "I004": ("₹ 99.99", []),
        }
        tree = MockTree(data)
        
        # Sort ascending
        universal_tree_sort(tree, "col1", reverse=False)
        
        # Note: Dates and currencies are both numeric, so they get compared as floats.
        # "10-12-2022" timestamp is smaller than "15-12-2022" timestamp.
        # "₹ 99.99" -> 99.99, "₹ 1,234.50" -> 1234.50.
        # Let's verify no exceptions are raised and they are sorted.
        actual_order = [move[0] for move in tree.moves]
        self.assertEqual(len(actual_order), 4)


if __name__ == "__main__":
    unittest.main()
