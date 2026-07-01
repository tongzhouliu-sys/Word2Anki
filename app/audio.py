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
    Concurrently generates TTS audio files for a list of words.
    """
    media_dir = Path(media_dir_str)
    media_dir.mkdir(parents=True, exist_ok=True)
    
    tasks = [generate_single_audio(word, voice, media_dir) for word in words]
    results = await asyncio.gather(*tasks)
    
    return {word.lower(): success for word, success in zip(words, results)}
