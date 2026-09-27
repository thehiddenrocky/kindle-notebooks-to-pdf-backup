#!/bin/bash

TEST_NAME=${1:-version}

# Determine the source directory containing the notebooks
# Supports both original_notebooks and original-notebooks,
# and checks for the hidden .notebooks folder inside.
if [ -d "original-notebooks/.notebooks" ]; then
    ORIGINAL_DIR="original-notebooks/.notebooks"
elif [ -d "original_notebooks/.notebooks" ]; then
    ORIGINAL_DIR="original_notebooks/.notebooks"
elif [ -d "original-notebooks" ]; then
    ORIGINAL_DIR="original-notebooks"
else
    ORIGINAL_DIR="original_notebooks"
fi

echo "Source notebooks directory resolved to: $ORIGINAL_DIR"

OUTPUT_BASE="converted_notebooks/$TEST_NAME"
PDF_DIR="$OUTPUT_BASE/pdf"

CALIBRE_DEBUG="/Applications/calibre.app/Contents/MacOS/calibre-debug"
EBOOK_CONVERT="/Applications/calibre.app/Contents/MacOS/ebook-convert"

mkdir -p "$PDF_DIR"

for f in "$ORIGINAL_DIR"/*; do
    [ -e "$f" ] || continue
    
    name=$(basename "$f")
    
    # Skip items containing '!!' (which indicates eBooks/PDOCs/EBSPs rather than pure notebooks)
    if [[ "$name" == *"!!"* ]]; then
        echo "Skipping book/document item (contains !!): $name"
        continue
    fi

    # Skip Kindle Scribe system directories
    if [[ "$name" == "page_cache" || "$name" == "thumbnails" || "$name" == "clipboard" || "$name" == ".backups" ]]; then
        echo "Skipping Scribe system folder: $name"
        continue
    fi
    
    echo "===================================================="
    echo "STARTING: $name"
    echo "===================================================="

    # Define temporary EPUB path
    TEMP_EPUB="/tmp/${name}_temp.epub"

    # 1. Convert Scribe notebook to temporary EPUB
    echo "--- [LOG] Running KFX Conversion for $name to temporary EPUB ---"
    $CALIBRE_DEBUG -r "KFX Input" -- "$f" "$TEMP_EPUB"
    
    # Check if temporary EPUB creation succeeded
    if [ -f "$TEMP_EPUB" ]; then
        echo "--- [LOG] Intermediate EPUB successful ---"
        
        echo "--- [LOG] Running PDF Conversion for $name ---"
        # 2. Convert to PDF
        $EBOOK_CONVERT "$TEMP_EPUB" "$PDF_DIR/$name.pdf" \
            --pdf-page-numbers \
            --paper-size letter \
            --margin-left 0 --margin-right 0 --margin-top 0 --margin-bottom 0 \
            --verbose
            
        # Clean up temporary EPUB
        rm -f "$TEMP_EPUB"
    else
        echo "--- [ERROR] EPUB conversion failed for $name ---"
    fi
    
    echo "FINISHED: $name"
    echo ""
done

echo "Batch processing complete."
