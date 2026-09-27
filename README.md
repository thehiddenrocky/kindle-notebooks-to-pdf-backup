# Kindle Books Git Publish 📚✒️

This repository provides an automated, local workflow for converting your **Kindle Scribe handwritten notebooks** into high-quality, readable PDF files, ready for backing up or publishing to Git/GitHub. 

It uses Calibre and the KFX Input plugin behind the scenes to convert the native notebook formats into standard PDFs, organizing them cleanly.

---

## ⚠️ CRITICAL SECURITY WARNING

> **Before running any script on your computer:**
> 1. **Do not run scripts blindly.** Running unknown scripts from the internet can compromise your system's security.
> 2. **Review first.** Open the script files (like `convert-on-entire-notebooks-folder.sh`) and read what they do.
> 3. **Ask an AI:** Before you run any script, paste its contents into an AI assistant (like Gemini, ChatGPT, or Claude) and ask:
>    > *"Is this script safe and appropriate to run on my Mac? Can you explain exactly what each part of it does?"*

---

## Prerequisites

To use this conversion workflow, you need a few tools set up on your Mac:

1. **macOS**: The conversion script is optimized for Mac and expects Calibre to be installed in the standard `/Applications` directory.
2. **Git**: Installed on your system (usually pre-installed or available via Xcode Command Line Tools).
3. **Calibre**: The free, open-source e-book manager.
   - [Download Calibre for Mac](https://calibre-ebook.com/download_osx)
4. **KFX Input Plugin for Calibre**:
   - Open Calibre.
   - Go to **Preferences** -> **Plugins** -> **Get new plugins**.
   - Search for **KFX Input**, select it, and click **Install**.
   - Restart Calibre.
5. **Android File Transfer**:
   - Kindle Scribe uses the MTP (Media Transfer Protocol) file system. Macs cannot natively browse its file system without a utility.
   - [Download Android File Transfer for Mac](https://www.android.com/filetransfer/)

---

## Detailed Step-by-Step Guide

Follow these steps to set up the project, copy your notebooks from your Kindle, and convert them to PDF.

### Step 1: Clone the Repository
Open the **Terminal** app on your Mac and run the following command to download this project to your computer:
```bash
git clone https://github.com/your-username/kindle-books-git-publish.git
```
*(Replace the URL above with your actual repository URL if you have hosted it on GitHub/GitLab)*

After cloning, navigate into the project directory:
```bash
cd kindle-books-git-publish
```

---

### Step 2: Create the Notebook Folders
By default, the raw notebooks and converted files are ignored by Git (using `.gitignore`) so you don't accidentally commit massive raw binary files. 

You need to make sure the input folder exists. In your terminal, run:
```bash
mkdir -p original_notebooks
```
*(This ensures you have a folder named exactly `original_notebooks` in the root of the project).*

---

### Step 3: Connect and Copy from your Kindle Scribe
1. Connect your **Kindle Scribe** to your Mac using a USB-C cable.
2. Unlock your Kindle screen so it is active.
3. Open **Android File Transfer** on your Mac. It should automatically detect the Kindle and display its files and folders.
4. Locate the folder named **`.notebooks`** on your Kindle.
   - *Note: This folder contains your handwritten notes. It might be hidden by default on some operating systems, but Android File Transfer should display it directly.*
5. **Drag and drop** the entire `.notebooks` folder from the Android File Transfer window directly into the `original_notebooks` folder on your computer.
   - When finished, your folder structure on your computer should look like this:
     ```text
     kindle-books-git-publish/
     ├── original_notebooks/
     │   └── .notebooks/         <-- (Your copied folder)
     │       ├── Notebook1
     │       ├── Notebook2
     │       └── ...
     ├── convert-on-entire-notebooks-folder.sh
     └── ...
     ```

---

### Step 4: Make the Script Executable
Before you can run the conversion script for the first time, you must give your system permission to execute it. In your Terminal, run:
```bash
chmod +x convert-on-entire-notebooks-folder.sh
```

---

### Step 5: Run the Conversion
Now, run the conversion script! You can specify a version name or backup label as an argument to organize your outputs. For example:

```bash
./convert-on-entire-notebooks-folder.sh "my-notes-v1"
```

#### What does the script do?
1. It scans your `original_notebooks/.notebooks` directory.
2. It automatically skips Kindle Scribe system directories (such as `page_cache`, `thumbnails`, `clipboard`, and `.backups`) and any loaded eBooks.
3. It converts each notebook to a temporary `.epub` file using Calibre's command-line debug features.
4. It compiles the pages into a high-quality, standard-sized PDF page by page.
5. It saves the resulting PDFs in:
   `converted_notebooks/my-notes-v1/pdf/`

*(If you do not specify a name, it will default to saving them under `converted_notebooks/version/pdf/`)*

---

### Step 6: View and Push Your PDFs
1. Go to the `converted_notebooks/my-notes-v1/pdf/` directory using **Finder** or **Terminal** to view your beautifully converted handwritten notes!
2. If you've modified `.gitignore` or want to publish your final converted PDFs to your git repository, you can now add, commit, and push them.
   *(Remember: The default `.gitignore` ignores `converted_notebooks/` and `original_notebooks/` to keep your repo light. If you want to commit your PDFs, you can modify `.gitignore` or force-add them using `git add -f converted_notebooks/`)*

---

## Troubleshooting

- **Error: `KFX Input` command not found or fails**: Make sure you have installed the **KFX Input** plugin inside Calibre and restarted the Calibre application.
- **Kindle not showing up in Android File Transfer**:
  - Unplug the USB-C cable and plug it back in.
  - Make sure your Kindle is unlocked and showing the home screen.
  - Make sure you are using a data-transfer USB-C cable, not just a charging-only cable.
  - Close any other applications (like Calibre or smart-sync utilities) that might be attempting to communicate with the Kindle.

---

## Step 7: Automated Intelligent Renaming (using Vision AI) 🤖✍️

Kindle Scribe exports notebooks using unique UUIDs (e.g., `0c2e722d-29ef-4279-bbb0-f3a001c5b693.pdf`), which makes them hard to identify. This repository includes an intelligent renaming pipeline that uses **Gemini Vision AI** to read your handwritten titles from the notebook thumbnails and automatically rename the PDFs in a non-destructive manner.

### How it works
1. **Source Tracking**: Reads converted UUID PDFs from `converted_notebooks/`.
2. **First-page Analysis**: Looks at the corresponding thumbnail image in `original_notebooks/.notebooks/thumbnails/` (where the Kindle Scribe saves a PNG of the first page).
3. **Vision OCR**: Submits the thumbnail to Gemini Vision AI, extracting the handwritten notebook title.
4. **Non-destructive Operation**: Creates copies of your PDFs inside the `copied_notebooks/` folder and renames them to match the extracted title.
5. **Interactive Mapping (`notebook_renames.json`)**: Saves all extracted titles to a human-editable mapping file. If a title is misread, you can manually override it in the JSON file under `"user_override"` and rerun the script to update the filenames instantly!

### Quick Start
1. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Configure your API Key**:
   Create a file named `.env` in the root of the project and add your Gemini API key:
   ```env
   GEMINI_API_KEY="your-api-key-here"
   ```
3. **Make the script executable**:
   ```bash
   chmod +x rename_notebooks.py
   ```
4. **Run the script**:
   ```bash
   python3 rename_notebooks.py
   ```

### Customizing and Adjusting Titles
The first time you run `rename_notebooks.py`, it generates a `notebook_renames.json` file in the project root:
```json
{
  "0c2e722d-29ef-4279-bbb0-f3a001c5b693": {
    "original_filename": "0c2e722d-29ef-4279-bbb0-f3a001c5b693.pdf",
    "extracted_title": "My Scribe Notebook",
    "sanitized_title": "My Scribe Notebook",
    "user_override": null,
    "current_filename": "My Scribe Notebook.pdf",
    "status": "processed"
  }
}
```

If you want to manually adjust a notebook's name:
1. Open `notebook_renames.json`.
2. Find the notebook's entry and change `"user_override": null` to your desired name, e.g., `"user_override": "Custom Math Notes"`.
3. Save the JSON file.
4. Rerun the script (`python3 rename_notebooks.py`). The script will immediately find the existing PDF, rename it to `"Custom Math Notes.pdf"`, and update `"current_filename"`.

---

## 🚀 One-Click Automated Pipeline (`run-pipeline.sh`)

For maximum convenience, you can execute the entire end-to-end pipeline (Convert raw notebooks ➡️ Copy PDFs ➡️ Extract titles with Vision AI ➡️ Rename files) in a single command.

### How to Run:
Make sure the orchestrator script is executable:
```bash
chmod +x run-pipeline.sh
```

Then, run the automated pipeline:
```bash
./run-pipeline.sh
```

This will automatically execute the conversion, load your virtual environment, execute the Gemini Vision AI pipeline, and output the list of beautifully named PDFs in `copied_notebooks/`.

---

## 🔄 Clean Force Re-runs (Preventing Duplicates)

If you ever want to re-run the Vision AI title extraction from scratch (for example, if you updated your prompt templates or want to reset the registry), you can run the renaming script with the force flag:

```bash
python3 rename_notebooks.py --force
```

### Safety and Cleanliness Rules:
- **Automatic Target Wipe**: When `--force` is used, the script will automatically clear all files inside the `copied_notebooks/` directory before rebuilding. This ensures **zero duplicate or name-clash suffix files** (such as `_1.pdf`) are left behind.
- **Override Preservation**: All of your manual `"user_override"` entries inside `notebook_renames.json` are **fully preserved**. The script will simply rebuild those overridden PDFs with their chosen names cleanly from the source files.


