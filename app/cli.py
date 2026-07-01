import argparse
import sys
import yaml
import logging
import asyncio
from pathlib import Path

from app.importer import extract_words_from_docx
from app.db import get_pending_words, init_db, mark_done, mark_failed
from app.ai import process_batch
from app.audio import generate_batch_audio
from app.anki import check_anki_connection, ensure_deck_exists, ensure_model_exists, push_card_to_anki

# Ensure logs directory exists
Path("logs").mkdir(exist_ok=True)

# Configure logging
logger = logging.getLogger("word2anki")
logger.setLevel(logging.DEBUG)

# Clear existing handlers if any to avoid duplication
if logger.handlers:
    logger.handlers.clear()

# File handler (detailed debugging log)
file_handler = logging.FileHandler("logs/word2anki.log", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# Console handler (clean progress updates)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

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
    
    return {
        "deck_name": "Word2Anki",
        "claude_model": "claude-3-5-sonnet-20241022",
        "voice": "en-US-AvaNeural",
        "db_path": "word2anki.db",
        "batch_size": 15
    }

def build_command(file_path: str) -> None:
    """
    Orchestrates the entire Word2Anki import & generation pipeline.
    """
    config = load_config()
    db_path = config.get("db_path", "word2anki.db")
    
    # 1. Read word document and extract words
    logger.info(f"Reading Word document: {file_path}")
    try:
        all_words = extract_words_from_docx(file_path)
    except Exception as e:
        logger.error(f"Error parsing Word file: {e}")
        sys.exit(1)
        
    logger.info(f"Extracted {len(all_words)} unique words from document.")
    
    if not all_words:
        logger.warning("No words found in the document. Exiting.")
        return

    # 2. Initialize SQLite DB and get pending words
    try:
        init_db(db_path)
        pending_words = get_pending_words(db_path, all_words)
    except Exception as e:
        logger.error(f"SQLite DB operation failed: {e}")
        sys.exit(1)
        
    total_words = len(all_words)
    completed_count = total_words - len(pending_words)
    logger.info(f"Status update: {completed_count}/{total_words} words already completed.")
    
    if not pending_words:
        logger.info("All words are already completed! Nothing to do.")
        return

    # 3. Check Anki connect, ensure deck and note type exist
    logger.info("Checking Anki connection...")
    if not check_anki_connection():
        logger.error("Anki is not running. Please launch Anki and make sure AnkiConnect is installed and running.")
        sys.exit(1)
        
    deck_name = config.get("deck_name", "Word2Anki")
    try:
        ensure_deck_exists(deck_name)
        ensure_model_exists()
    except Exception as e:
        logger.error(f"Failed to verify/create deck or model: {e}")
        sys.exit(1)

    # 4. Process pending words in batches
    batch_size = config.get("batch_size", 15)
    voice = config.get("voice", "en-US-AvaNeural")
    api_model = config.get("api_model", "gpt-4o-mini")
    api_base_url = config.get("api_base_url", "https://api.openai.com/v1")
    
    logger.info(f"Starting pipeline. Processing {len(pending_words)} words in batches of {batch_size}...")
    
    processed_count = completed_count
    
    total_batches = ((len(pending_words) - 1) // batch_size) + 1
    
    for idx_batch, i in enumerate(range(0, len(pending_words), batch_size), 1):
        batch = pending_words[i:i+batch_size]
        logger.info(f"--- Processing Batch {idx_batch}/{total_batches} ({len(batch)} words) ---")
        
        # A. Call API to generate explanations (handles caching internally)
        ai_data = {}
        try:
            ai_data = process_batch(batch, api_model, api_base_url)
        except Exception as e:
            logger.error(f"Failed to process batch {batch}: {e}")
            for w in batch:
                mark_failed(db_path, w, f"Batch generation failed: {e}")
            continue
            
        # B. Call Edge TTS to generate audios concurrently
        successful_ai_words = [w for w in batch if w.lower() in ai_data]
        if successful_ai_words:
            try:
                # generate_batch_audio is async
                asyncio.run(generate_batch_audio(successful_ai_words, voice, media_dir_str="media"))
            except Exception as e:
                logger.warning(f"Audio generation encountered error: {e}. Pushing cards anyway.")
                
        # C. Push each word's card to Anki and update DB status
        for w in batch:
            w_lower = w.lower()
            processed_count += 1
            progress_pct = (processed_count / total_words) * 100
            
            if w_lower not in ai_data:
                logger.error(f"[{processed_count}/{total_words}] ({progress_pct:.1f}%) ❌ {w} (Failed to generate AI content)")
                mark_failed(db_path, w, "Failed to generate AI content")
                continue
                
            word_data = ai_data[w_lower]
            try:
                push_card_to_anki(deck_name, word_data, media_dir_str="media")
                mark_done(db_path, w)
                logger.info(f"[{processed_count}/{total_words}] ({progress_pct:.1f}%) ✅ {w}")
            except Exception as e:
                error_msg = f"Failed to push card: {e}"
                logger.error(f"[{processed_count}/{total_words}] ({progress_pct:.1f}%) ❌ {w} ({error_msg})")
                mark_failed(db_path, w, error_msg)

    logger.info("Pipeline run complete.")

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
