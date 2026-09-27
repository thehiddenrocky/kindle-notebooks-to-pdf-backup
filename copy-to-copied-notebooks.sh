#!/bin/bash

# Define directories
SRC_DIR="converted_notebooks"
DEST_DIR="copied_notebooks"

echo "===================================================="
echo "STARTING: Copying converted PDFs to $DEST_DIR"
echo "===================================================="

# Create the destination directory if it doesn't exist
mkdir -p "$DEST_DIR"

# Check if source directory exists
if [ ! -d "$SRC_DIR" ]; then
    echo "Error: Source directory '$SRC_DIR' does not exist."
    echo "Please run './convert-on-entire-notebooks-folder.sh' first to generate converted PDFs."
    exit 1
fi

# Find all PDFs in converted_notebooks and copy them to copied_notebooks
# Using -f in cp to overwrite and -v for verbose output
find "$SRC_DIR" -name "*.pdf" -exec cp -f -v {} "$DEST_DIR"/ \;

echo "===================================================="
echo "FINISHED: All PDFs successfully copied to $DEST_DIR!"
echo "===================================================="
