import os
import json
import logging
import requests
from pathlib import Path

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

def fetch_words_from_api(words: list[str], api_key: str, api_base_url: str, model: str, timeout: int = 120) -> list[dict]:
    """
    Queries OpenAI-compatible API to fetch data for a batch of words.
    """
    prompt = generate_prompt(words)
    url = f"{api_base_url.rstrip('/')}/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system", 
                "content": "You are an expert English teacher. You output ONLY valid JSON arrays containing English word definitions with no surrounding text or markdown blocks."
            },
            {
                "role": "user", 
                "content": prompt
            }
        ],
        "temperature": 0.2
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=timeout)
    response.raise_for_status()
    res_json = response.json()
    
    try:
        response_text = res_json["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as parse_err:
        raise ValueError(f"Failed to parse API response structure: {res_json}") from parse_err
        
    return parse_json_array(response_text)

def process_batch(words: list[str], api_model: str, api_base_url: str, api_timeout: int = 120) -> dict[str, dict]:
    """
    Processes a batch of words by fetching details from OpenAI-compatible API (with fallback logic).
    Returns a mapping of word -> parsed_data.
    """
    load_env()
    api_key = os.environ.get("API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("API key not found. Please set API_KEY or OPENAI_API_KEY in .env")

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
    logger.info(f"Querying API model '{api_model}' for batch: {uncached_words}... (waiting for response)")
    try:
        batch_results = fetch_words_from_api(uncached_words, api_key, api_base_url, api_model, api_timeout)
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
            logger.info(f"Querying API individually for: {w}")
            try:
                single_results = fetch_words_from_api([w], api_key, api_base_url, api_model, api_timeout)
                if single_results and len(single_results) > 0:
                    item = single_results[0]
                    word_key = w.lower()
                    save_to_cache(word_key, item)
                    results[word_key] = item
                    logger.info(f"Successfully generated and cached (fallback): {word_key}")
                else:
                    raise ValueError("Empty response from API")
            except Exception as single_err:
                logger.error(f"Failed to generate for '{w}' in fallback: {single_err}")
                
    return results
