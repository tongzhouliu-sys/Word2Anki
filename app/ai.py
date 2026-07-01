import os
import json
import re
import logging
from pathlib import Path
from anthropic import Anthropic

logger = logging.getLogger("word2anki")

# Simple .env loader to avoid external dependencies
def load_env() -> None:
    env_path = Path(".env")
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    parts = line.split("=", 1)
                    key = parts[0].strip()
                    val = parts[1].strip()
                    # Strip quotes if present
                    if val.startswith('"') and val.endswith('"'):
                        val = val[1:-1]
                    elif val.startswith("'") and val.endswith("'"):
                        val = val[1:-1]
                    os.environ[key] = val

def get_cache_path(word: str) -> Path:
    cache_dir = Path("cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{word.lower()}.json"

def get_cached_word(word: str) -> dict | None:
    """
    Returns the cached word data if it exists, otherwise None.
    """
    path = get_cache_path(word)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read cache for '{word}': {e}. Recalculating.")
    return None

def save_to_cache(word: str, data: dict) -> None:
    """
    Saves the word data to local file cache.
    """
    path = get_cache_path(word)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to write cache for '{word}': {e}")

def parse_json_array(text: str) -> list[dict]:
    """
    Cleans markdown formatting and extracts the JSON array from response text.
    """
    text = text.strip()
    # Strip markdown markers
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    # Extract anything between the first '[' and last ']'
    start = text.find('[')
    end = text.rfind(']')
    if start != -1 and end != -1 and end > start:
        text = text[start:end+1]

    return json.loads(text)

def generate_prompt(words: list[str]) -> str:
    words_str = ", ".join(words)
    return f"""Please provide English learning details for the following words: {words_str}.

You must return a valid JSON array. Do not wrap the JSON in conversational filler, explanations, or extra text. Return ONLY the raw JSON array.
Each object in the array must correspond to a word and contain these exact keys: "word", "meaning_cn", "meaning_en", "example", "memory_tip".

Example output format:
[
  {{
    "word": "apple",
    "meaning_cn": "苹果 (名词)",
    "meaning_en": "A round fruit with red, green, or yellow skin and crisp white flesh.",
    "example": "He took a bite of a juicy red apple.",
    "memory_tip": "A-P-P-L-E: Picture a round red apple hanging on a tree."
  }}
]"""

def fetch_words_from_claude(words: list[str], client: Anthropic, model: str) -> list[dict]:
    """
    Queries Claude to fetch data for a batch of words.
    """
    prompt = generate_prompt(words)
    
    response = client.messages.create(
        model=model,
        max_tokens=4000,
        system="You are an expert English teacher. You output ONLY valid JSON arrays containing English word definitions with no surrounding text or markdown blocks.",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    response_text = response.content[0].text
    return parse_json_array(response_text)

def process_batch(words: list[str], model: str) -> dict[str, dict]:
    """
    Processes a batch of words by fetching details from Claude API (with fallback logic).
    Returns a mapping of word -> parsed_data.
    """
    load_env()
    api_key = os.environ.get("CLAUDE_API_KEY")
    if not api_key:
        raise ValueError("CLAUDE_API_KEY environment variable is not set. Please set it in .env")

    client = Anthropic(api_key=api_key)
    results = {}
    
    # 1. Filter out already cached words
    uncached_words = []
    for w in words:
        cached_data = get_cached_word(w)
        if cached_data:
            results[w.lower()] = cached_data
        else:
            uncached_words.append(w)
            
    if not uncached_words:
        return results

    # 2. Attempt batch call
    logger.info(f"Querying Claude API for batch: {uncached_words}")
    try:
        batch_results = fetch_words_from_claude(uncached_words, client, model)
        for item in batch_results:
            word_key = item.get("word", "").lower()
            if word_key in uncached_words:
                save_to_cache(word_key, item)
                results[word_key] = item
                logger.info(f"Successfully generated and cached: {word_key}")
    except Exception as e:
        logger.warning(f"Batch generation failed: {e}. Falling back to single-word queries...")
        
        # 3. Fallback to single-word calls
        for w in uncached_words:
            logger.info(f"Querying Claude API individually for: {w}")
            try:
                single_results = fetch_words_from_claude([w], client, model)
                if single_results and len(single_results) > 0:
                    item = single_results[0]
                    word_key = w.lower()
                    save_to_cache(word_key, item)
                    results[word_key] = item
                    logger.info(f"Successfully generated and cached (fallback): {word_key}")
                else:
                    raise ValueError("Empty response from Claude")
            except Exception as single_err:
                logger.error(f"Failed to generate for '{w}' in fallback: {single_err}")
                # We do not write to results, letting calling code know this word failed
                
    return results
