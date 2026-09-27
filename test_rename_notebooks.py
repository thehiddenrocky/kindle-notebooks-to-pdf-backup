#!/usr/bin/env python3
import unittest
import tempfile
import json
import shutil
from pathlib import Path

# Import functions to test from rename_notebooks
from rename_notebooks import (
    sanitize_filename,
    get_unique_target_path,
    load_registry,
    save_registry,
    MAPPING_FILE
)

class TestScribeRenamer(unittest.TestCase):
    
    def setUp(self):
        # Create a temporary directory for file-based tests
        self.test_dir = tempfile.TemporaryDirectory()
        self.test_path = Path(self.test_dir.name)
        
    def tearDown(self):
        # Clean up temporary directory
        self.test_dir.cleanup()
        
    def test_sanitize_filename(self):
        # Test basic sanitization
        self.assertEqual(sanitize_filename("Simple Title"), "Simple Title")
        
        # Test stripping quotes
        self.assertEqual(sanitize_filename('"Quoted Title"'), "Quoted Title")
        self.assertEqual(sanitize_filename("'Single Quoted'"), "Single Quoted")
        
        # Test slashes and colons are replaced by dashes
        self.assertEqual(sanitize_filename("Title / With / Slashes : Colons"), "Title - With - Slashes - Colons")
        
        # Test other forbidden characters are removed
        self.assertEqual(sanitize_filename("Invalid*?\"<>|Chars"), "InvalidChars")
        
        # Test consecutive whitespaces are consolidated
        self.assertEqual(sanitize_filename("  Title   with    spaces  "), "Title with spaces")
        
        # Test empty input
        self.assertEqual(sanitize_filename(""), "")
        self.assertEqual(sanitize_filename(None), "")

    def test_get_unique_target_path_no_collision(self):
        # When no file exists, the unique path should be exactly the desired name
        desired = "Notebook_A.pdf"
        unique_path = get_unique_target_path(self.test_path, desired, "dummy-uuid")
        self.assertEqual(unique_path.name, desired)
        self.assertEqual(unique_path.parent, self.test_path)

    def test_get_unique_target_path_with_collision(self):
        # If the file already exists, it should append _1, _2 etc.
        desired = "Notebook_A.pdf"
        
        # Create a dummy file to simulate collision
        (self.test_path / desired).write_text("dummy")
        
        unique_path1 = get_unique_target_path(self.test_path, desired, "dummy-uuid")
        self.assertEqual(unique_path1.name, "Notebook_A_1.pdf")
        
        # Create the second file
        (self.test_path / "Notebook_A_1.pdf").write_text("dummy")
        
        unique_path2 = get_unique_target_path(self.test_path, desired, "dummy-uuid")
        self.assertEqual(unique_path2.name, "Notebook_A_2.pdf")

    def test_load_save_registry(self):
        # Mock MAPPING_FILE
        temp_mapping_file = self.test_path / "test_renames.json"
        
        # Override the global MAPPING_FILE path in rename_notebooks module for this test
        import rename_notebooks
        original_mapping_file = rename_notebooks.MAPPING_FILE
        rename_notebooks.MAPPING_FILE = temp_mapping_file
        
        try:
            # Load from non-existent file should return empty dict
            self.assertEqual(load_registry(), {})
            
            # Save a dummy mapping
            dummy_data = {
                "uuid-123": {
                    "original_filename": "uuid-123.pdf",
                    "extracted_title": "Test Title",
                    "sanitized_title": "Test Title",
                    "user_override": None,
                    "current_filename": "Test Title.pdf",
                    "status": "processed"
                }
            }
            save_registry(dummy_data)
            
            # Load again and check contents
            loaded_data = load_registry()
            self.assertEqual(loaded_data["uuid-123"]["extracted_title"], "Test Title")
            self.assertEqual(loaded_data["uuid-123"]["status"], "processed")
            
        finally:
            # Restore original path
            rename_notebooks.MAPPING_FILE = original_mapping_file

if __name__ == "__main__":
    unittest.main()
