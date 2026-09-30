#!/usr/bin/env python3
import os
import sys
import json
import hashlib
import shutil
import logging
import argparse
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("scribe_transcriber")

# Paths
BASE_DIR = Path("/Users/akshenndragarg/Desktop/kindle-books-git-publish")
COPIED_PDF_DIR = BASE_DIR / "copied_notebooks"
OUTPUT_DIR = BASE_DIR / "transcribed_notes"
REGISTRY_FILE = BASE_DIR / "transcription_registry.json"

# Load environment variables from .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    logger.debug("python-dotenv is not installed. Skipping loading from .env")

# Retrieve Gemini API Key & Model
api_key = os.environ.get("GEMINI_API_KEY")
model_name = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")  # gemini-3.5-flash model

def initialize_gemini():
    """
    Attempts to initialize the Gemini client using either the new google-genai SDK 
    or the legacy google-generativeai SDK.
    Returns a client object and a generate function.
    """
    if not api_key:
        logger.error("GEMINI_API_KEY not found in environment variables or .env file.")
        logger.error("Please set GEMINI_API_KEY in your .env file or export it in your terminal.")
        sys.exit(1)

    # 1. Try google-genai (Modern SDK)
    try:
        from google import genai
        from google.genai import types
        logger.info("Successfully loaded modern 'google-genai' SDK for transcription.")
        client = genai.Client(api_key=api_key)
        
        def generate_with_modern(data_bytes, mime_type, prompt):
            response = client.models.generate_content(
                model=model_name,
                contents=[
                    types.Part.from_bytes(
                        data=data_bytes,
                        mime_type=mime_type,
                    ),
                    prompt
                ]
            )
            return response.text
        
        return generate_with_modern

    except ImportError:
        logger.debug("google-genai SDK not available. Trying google-generativeai fallback...")

    # 2. Try google-generativeai (Legacy SDK)
    try:
        import google.generativeai as genai_legacy
        logger.info("Successfully loaded legacy 'google-generativeai' SDK fallback for transcription.")
        genai_legacy.configure(api_key=api_key)
        model = genai_legacy.GenerativeModel(model_name)
        
        def generate_with_legacy(data_bytes, mime_type, prompt):
            response = model.generate_content([
                {
                    "mime_type": mime_type,
                    "data": data_bytes
                },
                prompt
            ])
            return response.text
            
        return generate_with_legacy

    except ImportError:
        logger.error("No compatible Gemini SDK found in python environment.")
        logger.error("Please run: pip install google-genai python-dotenv pypdf")
        sys.exit(1)

def calculate_md5(file_path: Path) -> str:
    """Calculates the MD5 checksum of a file to track changes."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def load_registry() -> dict:
    """Loads the transcription registry mapping file."""
    if REGISTRY_FILE.exists():
        try:
            with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading {REGISTRY_FILE}: {e}. Starting fresh.")
    return {}

def save_registry(registry: dict):
    """Saves the transcription registry mapping back to the JSON file."""
    try:
        with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)
        logger.debug("Transcription registry saved successfully.")
    except Exception as e:
        logger.error(f"Error saving transcription registry: {e}")

def run_transcription(force_reprocess=False):
    logger.info("Starting Kindle Scribe Notes Transcription Pipeline...")
    
    # Ensure directories exist
    if not OUTPUT_DIR.exists():
        logger.info(f"Output directory '{OUTPUT_DIR}' does not exist. Creating it.")
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
    if not COPIED_PDF_DIR.exists():
        logger.error(f"Source PDF directory '{COPIED_PDF_DIR}' does not exist.")
        logger.error("Please run rename_notebooks.py or the full pipeline first.")
        sys.exit(1)
        
    # Scan source directory for all PDFs
    source_pdfs = list(COPIED_PDF_DIR.glob("*.pdf"))
    if not source_pdfs:
        logger.warning(f"No PDF files found in '{COPIED_PDF_DIR}'. Work is complete or nothing to transcribe.")
        return
        
    # Load registry
    registry = load_registry()
    
    # If force, clear outputs and reset registry
    if force_reprocess:
        logger.info(f"Force transcription requested. Clearing all files inside '{OUTPUT_DIR}'...")
        if OUTPUT_DIR.exists():
            for item in OUTPUT_DIR.iterdir():
                try:
                    if item.is_file() or item.is_symlink():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                except Exception as e:
                    logger.error(f"Failed to delete {item} during cleanup: {e}")
        registry = {}
        
    # Prompt for notebook transcription
    transcription_prompt = (
        "You are an expert at transcribing handwritten notebooks.\n"
        "Your task is to accurately transcribe the attached handwritten notebook PDF document into highly readable, cleanly formatted Markdown.\n\n"
        "RULES:\n"
        "- Read all pages in the PDF sequentially.\n"
        "- Output the full transcription in clean Markdown format.\n"
        "- Use Markdown headers (`#`, `##`) to structure separate pages, sections, or clear thematic boundaries.\n"
        "- Preserve the original layout's intent, such as lists, bullet points, numbered items, and checkbox lists (`- [ ]` / `- [x]`).\n"
        "- If a page contains drawings, mind maps, sketches, or complex diagrams, describe them briefly inside HTML-like comment blocks, e.g., `<!-- [Sketch: description of diagram] -->`.\n"
        "- Correct minor handwritten typos if obvious, but prioritize literal accuracy of the notes.\n"
        "- Do NOT include any introductory or concluding thoughts. Output ONLY the markdown formatted transcription."
    )
    
    # Lazy loaded generator function
    generate_fn = None
    any_changes = False
    
    for pdf_path in source_pdfs:
        filename = pdf_path.name
        stem = pdf_path.stem
        logger.info(f"Evaluating file: {filename}")
        
        # Calculate file hash
        try:
            current_hash = calculate_md5(pdf_path)
        except Exception as e:
            logger.error(f"Failed to compute MD5 for {filename}: {e}")
            continue
            
        output_file_path = OUTPUT_DIR / f"{stem}.md"
        
        # Determine if we should skip
        if (
            filename in registry and 
            registry[filename].get("hash") == current_hash and 
            output_file_path.exists()
        ):
            logger.info(f"-> Skip: {filename} has not changed (matched MD5 hash).")
            continue
            
        # Initialize Gemini SDK on first call
        if generate_fn is None:
            generate_fn = initialize_gemini()
            
        logger.info(f"-> Transcribing: {filename} (hash mismatch or missing output)...")
        try:
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
                
            # Call Vision/Doc AI
            logger.info(f"Submitting full PDF to Gemini model ({model_name})...")
            transcription = generate_fn(pdf_bytes, "application/pdf", transcription_prompt)
            
            # Write transcription to output markdown file
            with open(output_file_path, "w", encoding="utf-8") as out_f:
                out_f.write(transcription)
                
            logger.info(f"Successfully wrote transcription to: {output_file_path.name}")
            
            # Update registry
            registry[filename] = {
                "hash": current_hash,
                "output_file": str(output_file_path.relative_to(BASE_DIR))
            }
            any_changes = True
            
        except Exception as e:
            logger.error(f"Failed to transcribe {filename}: {e}")
            # Save registry of successful items so far before moving on
            save_registry(registry)
            continue
            
    if any_changes:
        save_registry(registry)
        logger.info("Transcription registry updated successfully.")
        
    logger.info("Transcription pipeline execution complete!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Kindle Scribe Notebook Decoupled Handwriting-to-Text Transcriber")
    parser.add_argument(
        "-f", "--force", 
        action="store_true", 
        help="Force-reprocess and rebuild all transcriptions from scratch"
    )
    args = parser.parse_args()

    try:
        run_transcription(force_reprocess=args.force)
    except KeyboardInterrupt:
        logger.info("\nTranscription cancelled by user.")
        sys.exit(0)
