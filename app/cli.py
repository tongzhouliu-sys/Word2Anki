import argparse
import sys
import yaml
import logging
from pathlib import Path

from app.importer import extract_words_from_docx
from app.db import get_pending_words, init_db

# Configure simple logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("word2anki")

def load_config() -> dict:
    config_path = Path("config.yaml")
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                if config:
                    return config
        except Exception as e:
            logger.warning(f"Failed to read config.yaml: {e}. Using defaults.")
    
    # Default fallback config
    return {
        "deck_name": "Word2Anki",
        "claude_model": "claude-3-5-sonnet-20241022",
        "voice": "en-US-AvaNeural",
        "db_path": "word2anki.db",
        "batch_size": 15
    }

def build_command(file_path: str) -> None:
    """
    Executes the main pipeline (Stage 1 logic only for now).
    """
    config = load_config()
    db_path = config.get("db_path", "word2anki.db")
    
    # Step 1: Read word document and extract words
    logger.info(f"Reading Word document: {file_path}")
    try:
        all_words = extract_words_from_docx(file_path)
    except Exception as e:
        logger.error(f"Error parsing Word file: {e}")
        sys.exit(1)
        
    logger.info(f"Extracted {len(all_words)} unique words from document.")
    
    # Step 2: Initialize SQLite DB and get pending words
    logger.info(f"Initializing SQLite DB: {db_path}")
    try:
        init_db(db_path)
        pending_words = get_pending_words(db_path, all_words)
    except Exception as e:
        logger.error(f"SQLite DB operation failed: {e}")
        sys.exit(1)
        
    completed_count = len(all_words) - len(pending_words)
    logger.info(f"Status update: {completed_count}/{len(all_words)} words already completed.")
    logger.info(f"Pending words to process: {len(pending_words)}")
    
    if not pending_words:
        logger.info("All words are already processed! Nothing to do.")
        return

    # In Stage 1, we stop here and wait for user verification.
    logger.info("Stage 1 execution completed. Word list extracted and SQLite state initialized successfully.")

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Word2Anki - Convert Word Lists to Anki Cards with AI contents & TTS"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # build sub-command
    build_parser = subparsers.add_parser("build", help="Extract and build Anki deck from a .docx file")
    build_parser.add_argument("file", help="Path to the Word (.docx) file containing words")
    
    args = parser.parse_args()
    
    if args.command == "build":
        build_command(args.file)

if __name__ == "__main__":
    main()
