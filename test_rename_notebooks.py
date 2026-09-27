#!/usr/bin/env python3
import unittest
from pathlib import Path
import tempfile
import shutil
import json

from rename_notebooks import (
    sanitize_filename,
    get_unique_target_path,
    load_registry,
    save_registry
)

class TestRenameNotebooks(unittest.TestCase):
    def test_sanitize_filename(self):
        # Verify invalid characters are stripped or replaced
        self.assertEqual(sanitize_filename("Daily Journal: 27/09/2026"), "Daily Journal- 27-09-2026")
        self.assertEqual(sanitize_filename('"Book" *Title*?'), "Book Title")
        self.assertEqual(sanitize_filename("   My   Notebook   "), "My Notebook")
        self.assertEqual(sanitize_filename(""), "")
        self.assertEqual(sanitize_filename(None), "")

    def test_get_unique_target_path(self):
        # Create a temporary directory to test unique path collisions
        with tempfile.TemporaryDirectory() as tmp_dir:
            dir_path = Path(tmp_dir)
            
            # File does not exist yet, should return original name
            path1 = get_unique_target_path(dir_path, "test_file.pdf", "uuid-123")
            self.assertEqual(path1, dir_path / "test_file.pdf")
            
            # Create the file
            (dir_path / "test_file.pdf").touch()
            
            # File exists now, should append suffix _1
            path2 = get_unique_target_path(dir_path, "test_file.pdf", "uuid-123")
            self.assertEqual(path2, dir_path / "test_file_1.pdf")
            
            # Create the _1 file
            (dir_path / "test_file_1.pdf").touch()
            
            # File exists now, should append suffix _2
            path3 = get_unique_target_path(dir_path, "test_file.pdf", "uuid-123")
            self.assertEqual(path3, dir_path / "test_file_2.pdf")

if __name__ == "__main__":
    unittest.main()
