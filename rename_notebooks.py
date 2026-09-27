#!/usr/bin/env python3
import os
import sys
import re
import json
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
logger = logging.getLogger("scribe_renamer")

# UUID regex to identify Kindle Scribe notebooks
UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)

# Paths
BASE_DIR = Path("/Users/akshenndragarg/Desktop/kindle-books-git-publish")
SRC_PDF_DIR = BASE_DIR / "converted_notebooks" / "version" / "pdf"
TARGET_DIR = BASE_DIR / "copied_notebooks"
THUMBNAIL_DIR = BASE_DIR / "original_notebooks" / ".notebooks" / "thumbnails"
MAPPING_FILE = BASE_DIR / "notebook_renames.json"

# Load environment variables from .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    logger.debug("python-dotenv is not installed. Skipping loading from .env")

# Retrieve Gemini API Key
api_key = os.environ.get("GEMINI_API_KEY")
model_name = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")

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
        logger.info("Successfully loaded modern 'google-genai' SDK.")
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
        from PIL import Image
        import io
        logger.info("Successfully loaded legacy 'google-generativeai' SDK fallback.")
        genai_legacy.configure(api_key=api_key)
        model = genai_legacy.GenerativeModel(model_name)
        
        def generate_with_legacy(data_bytes, mime_type, prompt):
            if mime_type == "application/pdf":
                response = model.generate_content([
                    {
                        "mime_type": "application/pdf",
                        "data": data_bytes
                    },
                    prompt
                ])
                return response.text
            else:
                image = Image.open(io.BytesIO(data_bytes))
                response = model.generate_content([image, prompt])
                return response.text
            
        return generate_with_legacy

    except ImportError:
        logger.error("No compatible Gemini SDK found in python environment.")
        logger.error("Please run: pip install google-genai python-dotenv pillow pypdf")
        sys.exit(1)

def sanitize_filename(name: str) -> str:
    """
    Sanitizes a string to make it safe for filesystems (especially macOS/Unix).
    Removes forbidden characters, replaces whitespace/slashes, and keeps it neat.
    """
    if not name:
        return ""
    # Remove leading/trailing quotes often returned by LLMs
    name = name.strip().strip("'\"")
    # Replace slashes and colons (invalid on macOS) with dashes
    name = re.sub(r"[\/\\:]", "-", name)
    # Remove other invalid characters (Windows and control chars)
    name = re.sub(r"[\*\?\"<>\|]", "", name)
    # Replace consecutive whitespaces with a single space
    name = re.sub(r"\s+", " ", name)
    return name.strip()

def get_unique_target_path(directory: Path, desired_name: str, uuid: str) -> Path:
    """
    Generates a unique path within the directory for the desired name.
    If a collision occurs with a file belonging to a DIFFERENT notebook, 
    appends a counter (e.g. My_Notebook_1.pdf).
    """
    base_name = Path(desired_name).stem
    ext = Path(desired_name).suffix
    
    target_path = directory / desired_name
    counter = 1
    
    while target_path.exists():
        # Read notebook_renames.json to see if this existing file is indeed for this same UUID
        # If the existing file has a different name, or if we can't confirm, resolve collision.
        # But to be safe, if target_path exists and is a different file, we add a counter.
        # If it's the exact same file we are processing, we don't need a counter.
        # However, since we process each UUID sequentially, we can just check if we have a collision.
        target_path = directory / f"{base_name}_{counter}{ext}"
        counter += 1
        
    return target_path

def load_registry() -> dict:
    """Loads the UUID to title mapping from the JSON file."""
    if MAPPING_FILE.exists():
        try:
            with open(MAPPING_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading {MAPPING_FILE}: {e}. Starting fresh.")
    return {}

def save_registry(registry: dict):
    """Saves the registry mapping back to the JSON file with pretty formatting."""
    try:
        with open(MAPPING_FILE, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)
        logger.debug("Registry saved successfully.")
    except Exception as e:
        logger.error(f"Error saving registry: {e}")

def extract_pdf_page_one_bytes(pdf_path: Path) -> bytes:
    """
    Extracts page 1 of the PDF and returns its bytes.
    Uses pypdf for a pure-Python, zero-system-dependency approach.
    """
    from pypdf import PdfReader, PdfWriter
    import io
    
    reader = PdfReader(pdf_path)
    if not reader.pages:
        raise ValueError(f"The PDF {pdf_path} has no pages.")
        
    writer = PdfWriter()
    writer.add_page(reader.pages[0])
    
    out_buf = io.BytesIO()
    writer.write(out_buf)
    return out_buf.getvalue()

def run_pipeline(force_reprocess=False):
    logger.info("Starting Kindle Scribe Vision Renaming Pipeline...")
    
    # Ensure target directory exists
    if not TARGET_DIR.exists():
        logger.info(f"Target directory '{TARGET_DIR}' does not exist. Creating it.")
        TARGET_DIR.mkdir(parents=True, exist_ok=True)
        
    # Check if we have source PDFs
    if not SRC_PDF_DIR.exists():
        logger.error(f"Source PDF directory '{SRC_PDF_DIR}' does not exist.")
        logger.error("Please run './convert-on-entire-notebooks-folder.sh' first.")
        sys.exit(1)
        
    # Scan source directory for UUID PDFs
    source_pdfs = [f for f in SRC_PDF_DIR.glob("*.pdf") if UUID_PATTERN.match(f.stem)]
    if not source_pdfs:
        logger.warning(f"No UUID-named PDFs found in {SRC_PDF_DIR}.")
        
    # Load registry
    registry = load_registry()
    
    # If force_reprocess is specified, clear the target directory and reset entries
    if force_reprocess:
        logger.info(f"Force-reprocess requested. Clearing all files inside '{TARGET_DIR}' for a clean rebuild...")
        if TARGET_DIR.exists():
            for item in TARGET_DIR.iterdir():
                try:
                    if item.is_file() or item.is_symlink():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                except Exception as e:
                    logger.error(f"Failed to delete {item} during cleanup: {e}")

        logger.info("Resetting registry entries (preserving user overrides)...")
        for uuid, entry in registry.items():
            # Reset current filename since the target directory was wiped clean
            entry["current_filename"] = f"{uuid}.pdf"
            if not entry.get("user_override"):
                entry["extracted_title"] = None
                entry["sanitized_title"] = None
                entry["status"] = "pending"
        any_changes = True
    
    # Initialize Gemini Client (lazy load, only if we need to call the API)
    generate_content_fn = None
    
    # Prompt for Vision AI
    extraction_prompt = (
        "Analyze this Kindle Scribe notebook cover/first page (handwritten) and extract its title.\n\n"
        "JOURNAL DETECTION & UNIFORMITY RULES:\n"
        "- Look closely at the top of the page for any date (e.g., '22.9.2026', '27.9 Morning', 'September 22').\n"
        "- Check if the page is a personal journal, diary entry, daily log, or contains phrases like 'Daily Journal', 'Journal', or just a prominent date with lists like 'Top 3', 'Bad', 'Grateful for'.\n"
        "- If a date is found on a journal page, format the title uniformly as:\n"
        "  'Daily Journal DD.MM.YYYY' (e.g., 'Daily Journal 22.09.2026' or 'Daily Journal 27.09.2026').\n"
        "  Ensure the date is converted to DD.MM.YYYY or D.M.YYYY if year is missing, defaulting to the year 2026 if not specified but context matches (e.g. '22.9.2026' -> 'Daily Journal 22.09.2026').\n"
        "  If there's an additional time/qualifier like 'Morning' or 'Evening', append it, e.g. 'Daily Journal 27.09.2026 Morning'.\n\n"
        "GENERAL TITLE RULES:\n"
        "- If it is NOT a journal, identify the main handwritten heading, title, or first line of text.\n"
        "- Return ONLY the sanitized plain text title (max 5-6 words). No intro/outro, no quotation marks, no markdown.\n"
        "- If the page is completely blank or has no readable text, return 'Untitled'.\n\n"
        "Output format: Return ONLY the final title as a single line of text."
    )
    
    # Keep track of changes
    any_changes = False
    
    for pdf_path in source_pdfs:
        uuid = pdf_path.stem
        logger.info(f"Processing notebook UUID: {uuid}")
        
        # Initialize registry entry if missing
        if uuid not in registry:
            registry[uuid] = {
                "original_filename": f"{uuid}.pdf",
                "extracted_title": None,
                "sanitized_title": None,
                "user_override": None,
                "current_filename": f"{uuid}.pdf",
                "status": "pending"
            }
            any_changes = True
            
        entry = registry[uuid]
        
        # 1. Determine Title (API Call if needed)
        if not entry["extracted_title"]:
            if not pdf_path.exists():
                logger.warning(f"No PDF found for {uuid} at {pdf_path}. Using fallback.")
                entry["extracted_title"] = "Untitled"
                entry["sanitized_title"] = "Untitled"
                entry["status"] = "untitled_fallback"
                any_changes = True
            else:
                # We have the PDF! Let's query Vision AI with Page 1
                if generate_content_fn is None:
                    generate_content_fn = initialize_gemini()
                    
                logger.info(f"Extracting handwritten title using Gemini for {uuid} (from PDF Page 1)...")
                try:
                    pdf_page_bytes = extract_pdf_page_one_bytes(pdf_path)
                    
                    raw_title = generate_content_fn(pdf_page_bytes, "application/pdf", extraction_prompt)
                    extracted_title = raw_title.strip()
                    sanitized_title = sanitize_filename(extracted_title)
                    
                    if not sanitized_title:
                        sanitized_title = "Untitled"
                        
                    logger.info(f"Successfully extracted title: '{extracted_title}' -> sanitized: '{sanitized_title}'")
                    
                    entry["extracted_title"] = extracted_title
                    entry["sanitized_title"] = sanitized_title
                    entry["status"] = "processed"
                    any_changes = True
                    
                except Exception as e:
                    logger.error(f"Failed to extract title for {uuid} via Gemini: {e}")
                    entry["status"] = "api_error"
                    any_changes = True
                    # Continue with next files, saving what we did
                    save_registry(registry)
                    continue
        
        # 2. Determine target filename (User Override vs Extracted Title)
        chosen_title = entry["user_override"] if entry["user_override"] else entry["sanitized_title"]
        if not chosen_title:
            chosen_title = "Untitled"
            
        target_filename = f"{chosen_title}.pdf"
        current_filename = entry.get("current_filename", f"{uuid}.pdf")
        
        # Paths in TARGET_DIR
        curr_file_path = TARGET_DIR / current_filename
        uuid_file_path = TARGET_DIR / f"{uuid}.pdf"
        
        # 3. Synchronize file state in target directory
        file_to_rename = None
        
        # Scenario A: The file is still named [UUID].pdf in TARGET_DIR
        if uuid_file_path.exists():
            file_to_rename = uuid_file_path
        # Scenario B: The file is at its recorded current_filename in TARGET_DIR
        elif curr_file_path.exists() and current_filename != f"{uuid}.pdf":
            file_to_rename = curr_file_path
        # Scenario C: The file is missing from TARGET_DIR but exists in SRC_PDF_DIR
        else:
            logger.info(f"File {current_filename} not found in target directory. Copying from source.")
            try:
                shutil.copy2(pdf_path, uuid_file_path)
                file_to_rename = uuid_file_path
            except Exception as e:
                logger.error(f"Failed to copy {pdf_path} to {uuid_file_path}: {e}")
                continue
                
        # 4. Perform the Renaming
        if file_to_rename:
            # If the current filename is already exactly the target filename, we are done!
            if file_to_rename.name == target_filename:
                logger.debug(f"File for {uuid} is already correctly named '{target_filename}'.")
                if entry.get("current_filename") != target_filename:
                    entry["current_filename"] = target_filename
                    any_changes = True
            else:
                # Generate a unique path to resolve collisions
                unique_target_path = get_unique_target_path(TARGET_DIR, target_filename, uuid)
                actual_target_name = unique_target_path.name
                
                logger.info(f"Renaming: '{file_to_rename.name}' -> '{actual_target_name}'")
                try:
                    shutil.move(file_to_rename, unique_target_path)
                    entry["current_filename"] = actual_target_name
                    any_changes = True
                except Exception as e:
                    logger.error(f"Failed to rename {file_to_rename.name} to {actual_target_name}: {e}")
                    
    # Save the registry at the end of the run (or on any changes)
    if any_changes:
        save_registry(registry)
        logger.info("Registry updated successfully.")
    
    logger.info("Kindle Scribe Vision Renaming Pipeline complete!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Kindle Scribe Intelligent Renaming Pipeline (Vision AI)")
    parser.add_argument(
        "-f", "--force", 
        action="store_true", 
        help="Force-reprocess and rebuild all titles via Vision AI (preserving user overrides)"
    )
    args = parser.parse_args()

    try:
        run_pipeline(force_reprocess=args.force)
    except KeyboardInterrupt:
        logger.info("\nPipeline execution cancelled by user.")
        sys.exit(0)
