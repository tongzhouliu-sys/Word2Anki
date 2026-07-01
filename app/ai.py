import os
import json
import logging
import requests
import re
from pathlib import Path
from app.normalizer import normalize_for_ai, normalize_for_ai_retry

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
    # Sanitize word to make it a safe filename (replace slashes, etc.)
    safe_name = re.sub(r'[\\/*?:"<>|]', '_', word.lower())
    return cache_dir / f"{safe_name}.json"

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

def combine_definitions(raw_word: str, items: list[dict]) -> dict:
    """
    Combines the explanations of multiple normalized words into a single definition dictionary.
    """
    if not items:
        return {
            "word": raw_word,
            "meaning_cn": "No meaning found",
            "meaning_en": "No meaning found",
            "example": "No example found",
            "memory_tip": "No memory tip found"
        }
    if len(items) == 1:
        data = items[0].copy()
        data["word"] = raw_word
        return data
        
    # Combine fields using <br> for HTML rendering in Anki
    meaning_cn = "<br>".join([f"<b>{item.get('word', '')}</b>: {item.get('meaning_cn', '')}" for item in items])
    meaning_en = "<br>".join([f"<b>{item.get('word', '')}</b>: {item.get('meaning_en', '')}" for item in items])
    example = "<br>".join([f"<b>{item.get('word', '')}</b>: {item.get('example', '')}" for item in items])
    memory_tip = "<br>".join([f"<b>{item.get('word', '')}</b>: {item.get('memory_tip', '')}" for item in items])
    
    return {
        "word": raw_word,
        "meaning_cn": meaning_cn,
        "meaning_en": meaning_en,
        "example": example,
        "memory_tip": memory_tip
    }

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

    # Map raw words to normalized word lists
    raw_to_normalized = {w: normalize_for_ai(w) for w in uncached_words}
    
    # Collect all unique normalized words needed across the batch
    unique_normalized = []
    for norm_list in raw_to_normalized.values():
        for nw in norm_list:
            if nw not in unique_normalized:
                unique_normalized.append(nw)

    # 2. Attempt batch call using normalized words
    if unique_normalized:
        logger.info(f"Querying API model '{api_model}' for normalized batch: {unique_normalized}... (waiting for response)")
        try:
            batch_results = fetch_words_from_api(unique_normalized, api_key, api_base_url, api_model, api_timeout)
            api_response_dict = {item.get("word", "").lower(): item for item in batch_results if "word" in item}
            
            # Map back to raw words, combine and save
            for w in uncached_words:
                norm_list = raw_to_normalized[w]
                missing = [nw for nw in norm_list if nw.lower() not in api_response_dict]
                if missing:
                    continue
                
                combined = combine_definitions(w, [api_response_dict[nw.lower()] for nw in norm_list])
                save_to_cache(w, combined)
                results[w.lower()] = combined
                logger.info(f"Successfully generated and cached: {w}")
        except Exception as e:
            logger.warning(f"Batch generation failed: {e}. Falling back to single-word queries...")
        
    # 3. Fallback to single-word calls for remaining words
    for w in uncached_words:
        if w.lower() in results:
            continue
            
        logger.info(f"Querying API individually for: {w}")
        norm_list = raw_to_normalized[w]
        try:
            word_items = []
            for nw in norm_list:
                logger.info(f"Querying single normalized word: {nw}")
                single_results = fetch_words_from_api([nw], api_key, api_base_url, api_model, api_timeout)
                if single_results and len(single_results) > 0:
                    word_items.append(single_results[0])
                else:
                    raise ValueError(f"Empty response from API for normalized word '{nw}'")
            
            if len(word_items) == len(norm_list):
                combined = combine_definitions(w, word_items)
                save_to_cache(w, combined)
                results[w.lower()] = combined
                logger.info(f"Successfully generated and cached (fallback): {w}")
            else:
                raise ValueError("Failed to get definitions for all normalized parts")
                
        except Exception as single_err:
            logger.error(f"Failed to generate for '{w}' in fallback: {single_err}")
            
            # --- THIRD LAYER: RETRY FLOW ---
            logger.info(f"Retrying generation with aggressive normalization for: {w}")
            try:
                norm_list_retry = normalize_for_ai_retry(w)
                logger.info(f"Normalized for retry: {norm_list_retry}")
                if not norm_list_retry:
                    raise ValueError(f"Aggressive normalization returned empty list for '{w}'")
                    
                word_items_retry = []
                for nw in norm_list_retry:
                    logger.info(f"Querying single retry normalized word: {nw}")
                    single_results = fetch_words_from_api([nw], api_key, api_base_url, api_model, api_timeout)
                    if single_results and len(single_results) > 0:
                        word_items_retry.append(single_results[0])
                    else:
                        raise ValueError(f"Empty response from API for retry word '{nw}'")
                
                if len(word_items_retry) == len(norm_list_retry):
                    combined = combine_definitions(w, word_items_retry)
                    save_to_cache(w, combined)
                    results[w.lower()] = combined
                    logger.info(f"Successfully generated and cached (retry): {w}")
                else:
                    raise ValueError("Failed to get definitions in retry")
            except Exception as retry_err:
                logger.error(f"Failed to generate for '{w}' even after retry: {retry_err}")
                
    return results
