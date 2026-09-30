#!/usr/bin/env python3
import unittest
from pathlib import Path
import tempfile
import json
import shutil

from transcribe_notebooks import (
    calculate_md5,
    load_registry,
    save_registry
)

class TestTranscribeNotebooks(unittest.TestCase):
    def test_calculate_md5(self):
        # Create a temp file with known content
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
            tmp_file.write(b"Hello Kindle Scribe Notebooks!")
            tmp_file.close()

        try:
            # Expected md5 hash of "Hello Kindle Scribe Notebooks!"
            import hashlib
            expected = hashlib.md5(b"Hello Kindle Scribe Notebooks!").hexdigest()
            actual = calculate_md5(tmp_path)
            self.assertEqual(actual, expected)
        finally:
            tmp_path.unlink()

    def test_registry_load_and_save(self):
        # Create a temp folder and mock registry paths
        with tempfile.TemporaryDirectory() as tmp_dir:
            dir_path = Path(tmp_dir)
            
            # Monkeypatch the module's REGISTRY_FILE variable
            import transcribe_notebooks
            original_registry_file = transcribe_notebooks.REGISTRY_FILE
            transcribe_notebooks.REGISTRY_FILE = dir_path / "mock_transcription_registry.json"
            
            try:
                # Initially registry is empty
                reg = load_registry()
                self.assertEqual(reg, {})
                
                # Save registry
                test_data = {
                    "note.pdf": {
                        "hash": "abc123hash",
                        "output_file": "transcribed_notes/note.md"
                    }
                }
                save_registry(test_data)
                
                # Load again
                loaded_reg = load_registry()
                self.assertEqual(loaded_reg["note.pdf"]["hash"], "abc123hash")
                self.assertEqual(loaded_reg["note.pdf"]["output_file"], "transcribed_notes/note.md")
                
            finally:
                # Restore original
                transcribe_notebooks.REGISTRY_FILE = original_registry_file

if __name__ == "__main__":
    unittest.main()
