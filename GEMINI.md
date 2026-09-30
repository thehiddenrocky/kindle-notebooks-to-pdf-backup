# Kindle Books Git Publish - Project Instructions

This document serves as the developer's guide and instruction manual for the **Kindle Books Git Publish** workspace. It outlines the project's purpose, architecture, setup requirements, key command references, and development conventions.

---

## 1. Project Overview

### Purpose
The **Kindle Books Git Publish** project provides an automated, local workflow on macOS for:
1. Converting raw **Kindle Scribe handwritten notebooks** (MTP-based KFX files) into readable standard PDFs.
2. Flattening and copying converted files to a clean output directory.
3. Automatically identifying and renaming notebooks using **Gemini Vision AI** to read handwritten titles from first-page/thumbnail previews, saving you from navigating unidentifiable UUID filenames.
4. Managing names interactively via a local registry (`notebook_renames.json`) with manual user overrides.

### Architecture & Components
The repository operates as a sequential two-stage pipeline, orchestrated either individually or via a single-command wrapper script:

*   **Stage 1: Notebook-to-PDF Conversion (`convert-on-entire-notebooks-folder.sh`)**
    *   **Input**: Kindle Scribe notebook folders placed inside `original_notebooks/.notebooks/` (copied via MTP / Android File Transfer).
    *   **Logic**: Scans the input folder, filtering out Kindle system directories (`page_cache`, `thumbnails`, `clipboard`, `.backups`) and non-notebook eBooks containing `!!` in their names. It utilizes **Calibre's command-line debug features** (`calibre-debug -r "KFX Input"`) to generate an intermediate EPUB, and then invokes `ebook-convert` to build formatted Letter-size PDFs.
    *   **Output**: Converted PDFs stored under `converted_notebooks/<version_name>/pdf/`.
*   **Stage 2: Vision AI Renaming & Registry Sync (`rename_notebooks.py`)**
    *   **Input**: The converted PDFs from Stage 1.
    *   **Logic**: Utilizes **Gemini Vision AI** to inspect Page 1 of each PDF and extract handwritten titles (with built-in formatting templates for Daily Journals and regular notes). It maintains a registry file `notebook_renames.json` to keep track of processed UUIDs.
    *   **User Overrides**: Allows developers/users to set custom names under `"user_override"` in the JSON registry. If set, subsequent runs prioritize the override name.
    *   **Copying & Deduping**: Copied and renamed PDFs are placed inside `copied_notebooks/`. If a title collision occurs, a unique numerical suffix (e.g., `_1.pdf`) is appended.
    *   **Force Re-runs**: Supports `--force` execution, which wipes the output directory `copied_notebooks/` and re-runs Vision API calls for all notebooks while strictly preserving existing manual `"user_override"` names in the JSON registry.
*   **Stage 3: Handwriting-to-Text Transcription (`transcribe_notebooks.py`)**
    *   **Input**: The renamed PDFs in `copied_notebooks/`.
    *   **Logic**: Implements MD5-based change tracking using a dedicated registry (`transcription_registry.json`). It submits unmodified/changed notebooks to the Gemini API (`gemini-3.5-flash`) for multi-page handwritten-to-Markdown transcription.
    *   **Output**: Rich Markdown files (`.md`) placed inside `transcribed_notes/`.
    *   **Force Re-runs**: Supports `--force` execution to wipe all transcriptions and regenerate them from scratch.
*   **Stage Orchestrator: Pipeline Overlord (`run-pipeline.sh`)**
    *   Checks system prerequisites (Calibre.app location).
    *   Runs the Stage 1 conversion script (passing arguments forward).
    *   Determines the correct Python runtime (virtual environment vs. global).
    *   Runs the Stage 2 Vision AI renaming python script.
    *   Runs the Stage 3 handwriting-to-text transcription script.

### Key Technologies
*   **Bash & Shell Tools**: Native macOS scripts, Calibre CLI (`calibre-debug`, `ebook-convert`), Unix `find` and `cp`.
*   **Python 3**: Core language for renaming, orchestrating Vision AI, and formatting.
*   **Google Gemini SDK**: Connects to Gemini models (defaults to `gemini-3.5-flash`). Uses the modern `google-genai` SDK with a fallback to the legacy `google-generativeai` package.
*   **pypdf**: Used for pure-Python extraction of PDF Page 1 bytes to submit to Vision AI.
*   **Pillow (PIL)**: Optional fallback image loader for legacy SDK integrations.
*   **python-dotenv**: For loading `.env` variables (such as `GEMINI_API_KEY` and `GEMINI_MODEL`).

---

## 2. Building, Running, and Environment Setup

### System Prerequisites
1.  **macOS**: Optimized for Darwin; relies on standard Calibre installation path.
2.  **Calibre.app**: Installed in `/Applications/calibre.app`.
3.  **KFX Input Plugin**: Installed and enabled in Calibre (Preferences -> Plugins -> Get new plugins -> search and install "KFX Input").
4.  **Android File Transfer**: For copying handwritten `.notebooks` folder from Kindle Scribe via USB-C.

### Development Environment Setup
To set up Python dependencies locally:

```bash
# 1. Create a Python Virtual Environment
python3 -m venv venv

# 2. Activate the Virtual Environment
source venv/bin/activate

# 3. Install Dependencies
pip install -r requirements.txt

# 4. Set Up Environment Variables
# Create a .env file in the project root:
echo "GEMINI_API_KEY=\"your-gemini-api-key-here\"" > .env
echo "GEMINI_MODEL=\"gemini-3.5-flash\"" >> .env
```

### Key Running Commands

#### Orchestrated End-to-End Pipeline
Run the entire conversion and renaming pipeline in a single command:
```bash
# Ensure script permissions
chmod +x run-pipeline.sh convert-on-entire-notebooks-folder.sh copy-to-copied-notebooks.sh rename_notebooks.py

# Run standard pipeline (output folder defaults to converted_notebooks/version/pdf)
./run-pipeline.sh

# Run pipeline with custom subfolder tag
./run-pipeline.sh "my-notes-v1"
```

#### Running Stage 1 Separately (Conversion Only)
To run only the Calibre-based PDF converter:
```bash
./convert-on-entire-notebooks-folder.sh "my-notes-v1"
```

#### Running Stage 2 Separately (Renaming & Copying Only)
To run only the Gemini-based title extraction and renaming script:
```bash
# Standard incremental run
python3 rename_notebooks.py

# Force reprocess (wipes copied_notebooks/ and re-evaluates names, preserving user overrides)
python3 rename_notebooks.py --force
```

#### Running Stage 3 Separately (Transcription Only)
To run only the Gemini-based handwriting transcription script:
```bash
# Standard incremental run (only transcribes missing or changed notebooks using MD5 hashes)
python3 transcribe_notebooks.py

# Force transcription (wipes transcribed_notes/ and re-transcribes all notes from scratch)
python3 transcribe_notebooks.py --force
```

#### Running Standalone Flatten Script (Optional Helper)
To copy all converted PDFs from `converted_notebooks/` directly to `copied_notebooks/` without renaming:
```bash
./copy-to-copied-notebooks.sh
```

---

## 3. Development Conventions

### Coding Guidelines
*   **SDK Compatibility**: Always maintain backward compatibility with both legacy `google-generativeai` and modern `google-genai` SDKs. Follow the lazy-load initialization pattern inside `initialize_gemini()`.
*   **Non-Destructive Operations**: Never edit or rename source files in `converted_notebooks/` or `original_notebooks/`. All renames must copy the file to `copied_notebooks/` with their new names.
*   **Filtration Safety**: Skip system folders (`page_cache`, `thumbnails`, etc.) and loaded documents (`!!`) in shell/python scripts.
*   **Robust Filename Sanitization**: Ensure filenames are sanitized on macOS/Unix (e.g. replacing colons and slashes with dashes, stripping illegal characters like `* ? " < > |`, and shrinking whitespace).
*   **Registry-First Configuration**: Check the registry mapping file `notebook_renames.json` for custom names before performing any API requests. This saves API costs and respects user choices.
*   **Error Tolerance**: If one notebook conversion or rename fails, log the error and proceed to the remaining notebooks. Save the registry state continuously upon changes to prevent loss.

### Directory Mapping
*   `original_notebooks/`: Local staging of Scribe `.notebooks/` files. **[Ignored by Git]**
*   `converted_notebooks/`: Intermediate Calibre output, categorized by version folders. **[Ignored by Git]**
*   `copied_notebooks/`: Final user-facing output folder containing renamed PDFs. **[Ignored by Git]**
*   `transcribed_notes/`: Directory containing converted markdown text files of notebooks. **[Ignored by Git]**
*   `notebook_renames.json`: Local file registry tracking processed UUIDs, extracted titles, and user overrides. **[Ignored by Git]**
*   `transcription_registry.json`: Local file registry tracking processed transcriptions and their MD5 hashes. **[Ignored by Git]**
*   `.env`: Local environment configurations and credentials. **[Ignored by Git]**

### Testing Practices
The Python modules have unit tests included in `test_rename_notebooks.py` and `test_transcribe_notebooks.py`.

*   **Test Execution**:
    Run tests with the standard Python unittest runner:
    ```bash
    python3 -m unittest test_rename_notebooks.py test_transcribe_notebooks.py
    ```
*   **Adding New Tests**:
    When modifying `rename_notebooks.py` or `transcribe_notebooks.py`, add corresponding test cases inside the respective test script and execute the test suite to verify behavior.
