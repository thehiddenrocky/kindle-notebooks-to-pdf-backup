#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Setup formatting colors for beautiful outputs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=======================================================================${NC}"
echo -e "${BLUE}           KINDLE SCRIBE NOTEBOOK AUTOMATED PIPELINE OVERLORD          ${NC}"
echo -e "${BLUE}=======================================================================${NC}"

# Check for Calibre requirements (ebook-convert and calibre-debug)
if [ ! -d "/Applications/calibre.app" ]; then
    echo -e "${RED}[ERROR] Calibre.app not found in /Applications.${NC}"
    echo -e "${RED}Please install Calibre to support Kindle Scribe notebook conversion.${NC}"
    exit 1
fi

# Determine python command in virtual environment
PYTHON_CMD="venv/bin/python3"
if [ ! -f "$PYTHON_CMD" ]; then
    PYTHON_CMD="python3"
    echo -e "${YELLOW}[WARNING] Virtual environment python not found at 'venv/bin/python3'. Falling back to global '$PYTHON_CMD'.${NC}"
fi

# Step 1: Run the notebook-to-PDF conversion script
echo -e "\n${YELLOW}--- [STAGE 1] Converting Scribe Notebooks to PDFs ---${NC}"
if [ -f "./convert-on-entire-notebooks-folder.sh" ]; then
    # Pass any script arguments forward (e.g. custom version name)
    /bin/bash ./convert-on-entire-notebooks-folder.sh "$@"
else
    echo -e "${RED}[ERROR] Conversion script './convert-on-entire-notebooks-folder.sh' not found.${NC}"
    exit 1
fi

# Step 2: Run the Vision AI renaming and copying script
echo -e "\n${YELLOW}--- [STAGE 2] Extracting Titles and Renaming with Vision AI ---${NC}"
if [ -f "./rename_notebooks.py" ]; then
    $PYTHON_CMD ./rename_notebooks.py
else
    echo -e "${RED}[ERROR] Renaming script './rename_notebooks.py' not found.${NC}"
    exit 1
fi

# Step 3: Run the handwritten note transcription script
echo -e "\n${YELLOW}--- [STAGE 3] Transcribing Handwritten Notes to Markdown with Gemini AI ---${NC}"
if [ -f "./transcribe_notebooks.py" ]; then
    $PYTHON_CMD ./transcribe_notebooks.py
else
    echo -e "${RED}[ERROR] Transcription script './transcribe_notebooks.py' not found.${NC}"
    exit 1
fi

echo -e "\n${GREEN}=======================================================================${NC}"
echo -e "${GREEN}   PIPELINE COMPLETE: Notebooks converted, renamed, and transcribed!    ${NC}"
echo -e "${GREEN}=======================================================================${NC}"

# Display a count of renamed notebooks in the target folder
if [ -d "copied_notebooks" ]; then
    COUNT_PDF=$(find copied_notebooks -type f -name "*.pdf" | wc -l | tr -d ' ')
    echo -e "${GREEN}Total notebooks in 'copied_notebooks/': $COUNT_PDF${NC}"
fi

# Display a count of transcribed notes in the text folder
if [ -d "transcribed_notes" ]; then
    COUNT_TXT=$(find transcribed_notes -type f -name "*.md" | wc -l | tr -d ' ')
    echo -e "${GREEN}Total transcriptions in 'transcribed_notes/': $COUNT_TXT${NC}\n"
    ls -lh transcribed_notes/
fi
