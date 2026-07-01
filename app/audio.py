import asyncio
import logging
from pathlib import Path
import edge_tts

logger = logging.getLogger("word2anki")

async def generate_single_audio(word: str, voice: str, media_dir: Path) -> bool:
    """
    Generates TTS audio file for a single word if it does not already exist.
    """
    word_clean = word.strip().lower()
    output_path = media_dir / f"{word_clean}.mp3"
    
    if output_path.exists():
        logger.info(f"Audio cache found for '{word_clean}', skipping TTS.")
        return True
        
    try:
        communicate = edge_tts.Communicate(word, voice)
        await communicate.save(str(output_path))
        logger.info(f"Successfully generated TTS audio for '{word_clean}'.")
        return True
    except Exception as e:
        logger.error(f"Failed to generate TTS audio for '{word_clean}': {e}")
        return False

async def generate_batch_audio(words: list[str], voice: str, media_dir_str: str = "media") -> dict[str, bool]:
    """
    Generates TTS audio files for a list of words.
    Sequentially processes each word, sleeping for 1 second after each API request to prevent rate limiting.
    """
    media_dir = Path(media_dir_str)
    media_dir.mkdir(parents=True, exist_ok=True)
    
    results = {}
    for idx, word in enumerate(words):
        word_clean = word.strip().lower()
        output_path = media_dir / f"{word_clean}.mp3"
        
        is_cached = output_path.exists()
        
        success = await generate_single_audio(word, voice, media_dir)
        results[word_clean] = success
        
        # Only throttle (sleep 1 second) if we did a network generation and there are more words
        if not is_cached and idx < len(words) - 1:
            logger.info("Throttling TTS: waiting 1 second before the next request...")
            await asyncio.sleep(1.0)
            
    return results
