import requests
import logging
from pathlib import Path

logger = logging.getLogger("word2anki")

ANKI_CONNECT_URL = "http://localhost:8765"

def invoke(action: str, **params) -> any:
    """
    Helper to send API requests to AnkiConnect.
    """
    payload = {
        "action": action,
        "version": 6,
        "params": params
    }
    try:
        response = requests.post(ANKI_CONNECT_URL, json=payload, timeout=5)
        response.raise_for_status()
        res_json = response.json()
        
        # Check standard AnkiConnect response fields
        if "error" in res_json and "result" in res_json:
            if res_json["error"]:
                raise Exception(res_json["error"])
            return res_json["result"]
        raise Exception("Invalid response format from AnkiConnect")
    except requests.exceptions.RequestException as e:
        raise ConnectionError(
            f"AnkiConnect not reachable at {ANKI_CONNECT_URL}. "
            "Please make sure Anki is open and AnkiConnect is installed and running."
        ) from e

def check_anki_connection() -> bool:
    """
    Performs a connection health check by querying the version of AnkiConnect.
    """
    try:
        version = invoke("version")
        logger.info(f"Connected to AnkiConnect. Version: {version}")
        return True
    except Exception as e:
        logger.error(f"AnkiConnect health check failed: {e}")
        return False

def ensure_deck_exists(deck_name: str) -> None:
    """
    Ensures that the target deck exists in Anki. Creates it if it does not.
    """
    existing_decks = invoke("deckNames")
    if deck_name not in existing_decks:
        logger.info(f"Deck '{deck_name}' not found. Creating deck...")
        invoke("createDeck", deck=deck_name)
        logger.info(f"Deck '{deck_name}' created successfully.")
    else:
        logger.info(f"Deck '{deck_name}' already exists.")

def ensure_model_exists() -> None:
    """
    Ensures that the 'Word2Anki_Basic' template/model exists in Anki.
    """
    model_name = "Word2Anki_Basic"
    existing_models = invoke("modelNames")
    if model_name in existing_models:
        logger.info(f"Model '{model_name}' already exists.")
        return

    logger.info(f"Model '{model_name}' not found. Creating model...")
    
    # Premium card styling configuration
    css = """
.card {
    font-family: 'Outfit', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 18px;
    text-align: center;
    color: #2D3748;
    background-color: #F7FAFC;
    padding: 24px;
    line-height: 1.6;
    max-width: 550px;
    margin: 0 auto;
    border-radius: 12px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}
.nightMode .card {
    color: #E2E8F0;
    background-color: #1A202C;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5);
}
.field-label {
    font-size: 14px;
    color: #718096;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 14px;
    margin-bottom: 2px;
    text-align: left;
    font-weight: 600;
}
.field-content {
    font-size: 18px;
    text-align: left;
    margin-bottom: 12px;
}
.word-title {
    font-size: 38px;
    font-weight: 800;
    color: #3182CE;
    margin-bottom: 20px;
}
.nightMode .word-title {
    color: #63B3ED;
}
"""

    card_templates = [
        {
            "Name": "Card 1",
            "Front": "<div class='card'><div class='word-title'>{{Word}}</div><div style='margin-top: 10px;'>{{Sound}}</div></div>",
            "Back": """<div class='card'>
  <div class='word-title'>{{Word}}</div>
  <div style='margin-top: 10px;'>{{Sound}}</div>
  <hr style='border: 0; border-top: 1px solid #E2E8F0; margin-bottom: 20px;'>
  
  <div class='field-label'>🇨🇳 Meaning (CN)</div>
  <div class='field-content'><b>{{Meaning_CN}}</b></div>
  
  <div class='field-label'>🇬🇧 Meaning (EN)</div>
  <div class='field-content'><i>{{Meaning_EN}}</i></div>
  
  <div class='field-label'>📝 Example Sentence</div>
  <div class='field-content'>{{Example}}</div>
  
  <div class='field-label'>💡 Memory Tip</div>
  <div class='field-content' style='color: #4A5568;'>{{Memory_Tip}}</div>
</div>"""
        }
    ]

    invoke(
        "createModel",
        modelName=model_name,
        inOrderFields=["Word", "Meaning_CN", "Meaning_EN", "Example", "Memory_Tip", "Sound"],
        css=css,
        cardTemplates=card_templates
    )
    logger.info(f"Model '{model_name}' created successfully.")

def push_card_to_anki(deck_name: str, word_data: dict, media_dir_str: str = "media") -> None:
    """
    Uploads the local pronunciation file to Anki and adds the note to the target deck.
    """
    word = word_data["word"].strip()
    word_lower = word.lower()
    
    # 1. Upload media file if it exists
    media_dir = Path(media_dir_str)
    mp3_path = media_dir / f"{word_lower}.mp3"
    
    media_filename = ""
    if mp3_path.exists():
        # Prefix filename to ensure uniqueness in Anki's global media namespace
        media_filename = f"word2anki_{word_lower.replace(' ', '_')}.mp3"
        try:
            invoke(
                "storeMediaFile",
                filename=media_filename,
                path=str(mp3_path.resolve())
            )
            logger.info(f"Uploaded media file '{media_filename}' to Anki.")
        except Exception as media_err:
            logger.warning(f"Failed to upload media file for '{word}': {media_err}. Proceeding without audio.")
            media_filename = ""
            
    # 2. Add note
    fields = {
        "Word": word,
        "Meaning_CN": word_data.get("meaning_cn", ""),
        "Meaning_EN": word_data.get("meaning_en", ""),
        "Example": word_data.get("example", ""),
        "Memory_Tip": word_data.get("memory_tip", ""),
        "Sound": f"[sound:{media_filename}]" if media_filename else ""
    }
    
    note = {
        "deckName": deck_name,
        "modelName": "Word2Anki_Basic",
        "fields": fields,
        "options": {
            "allowDuplicate": False,
            "duplicateScope": "deck",
            "duplicateScopeOptions": {
                "deckName": deck_name,
                "checkChildren": False,
                "checkAllModels": False
            }
        },
        "tags": ["word2anki"]
    }
    
    try:
        invoke("addNote", note=note)
        logger.info(f"Successfully added card for '{word}' to deck '{deck_name}'.")
    except Exception as e:
        if "duplicate" in str(e).lower():
            logger.info(f"Card for '{word}' already exists in deck '{deck_name}', skipping addNote.")
        else:
            raise e
