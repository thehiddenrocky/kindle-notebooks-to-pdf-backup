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
EPUB_DIR="$OUTPUT_BASE/epub"
PDF_DIR="$OUTPUT_BASE/pdf"

CALIBRE_DEBUG="/Applications/calibre.app/Contents/MacOS/calibre-debug"
EBOOK_CONVERT="/Applications/calibre.app/Contents/MacOS/ebook-convert"

mkdir -p "$EPUB_DIR" "$PDF_DIR"

for f in "$ORIGINAL_DIR"/*; do
    [ -e "$f" ] || continue
    
    name=$(basename "$f")
    
    # Skip PDOC (Personal Documents) items
    if [[ $(echo "$name" | tr '[:lower:]' '[:upper:]') == *"PDOC"* ]]; then
        echo "Skipping PDOC item: $name"
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

    # 1. Convert to EPUB
    # We remove the redirect so everything streams to the terminal
    echo "--- [LOG] Running KFX Conversion for $name ---"
    $CALIBRE_DEBUG -r "KFX Input" -- "$f" "$EPUB_DIR/$name.epub"
    
    # Check if EPUB creation succeeded
    if [ -f "$EPUB_DIR/$name.epub" ]; then
        echo "--- [LOG] Conversion to EPUB successful ---"
        
        echo "--- [LOG] Running PDF Conversion for $name ---"
        # 2. Convert to PDF
        $EBOOK_CONVERT "$EPUB_DIR/$name.epub" "$PDF_DIR/$name.pdf" \
            --pdf-page-numbers \
            --paper-size letter \
            --margin-left 0 --margin-right 0 --margin-top 0 --margin-bottom 0 \
            --verbose
    else
        echo "--- [ERROR] EPUB conversion failed for $name ---"
    fi
    
    echo "FINISHED: $name"
    echo ""
done

echo "Batch processing complete."
