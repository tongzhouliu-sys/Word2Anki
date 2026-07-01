import re

def normalize_text(text: str) -> str:
    """
    Applies the First Layer normalization rules:
    1. Unicode normalization (smart quotes/dashes to standard)
    2. Remove leading number prefix (e.g. '1376.')
    3. Trim leading/trailing whitespace
    4. Remove trailing ellipsis
    5. Remove trailing punctuation
    6. Merge multiple consecutive spaces
    """
    if not text:
        return ""
    
    # 1. Unicode normalization
    replacements = {
        "’": "'",
        "‘": "'",
        "“": '"',
        "”": '"',
        "–": "-",  # en dash
        "—": "-"   # em dash
    }
    for orig, repl in replacements.items():
        text = text.replace(orig, repl)
        
    # 2. Remove leading number patterns like "1376." or "1376)"
    text = re.sub(r'^\s*\d+[\.\)]?\s*', '', text)
    
    # 3. Trim whitespace
    text = text.strip()
    
    # 4. Remove trailing ellipsis (e.g. ..., ...., …)
    text = re.sub(r'\s*(?:\.{3,}|…+)\s*$', '', text)
    
    # 5. Remove trailing punctuation (. , ; : ! ?)
    # Note: Only at the end of the text.
    text = re.sub(r'\s*[\.,;:!\?]+\s*$', '', text)
    
    # 6. Merge multiple consecutive spaces
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def normalize_for_ai(raw_text: str) -> list[str]:
    """
    Applies First Layer (cleaning) and Second Layer (slash splitting).
    Situation A: Entire text has no spaces -> Split by '/'
    Situation B: Text has spaces -> Keep intact
    """
    cleaned = normalize_text(raw_text)
    if not cleaned:
        return []
        
    if '/' in cleaned:
        # Check if the text contains any space
        if not any(c.isspace() for c in cleaned):
            # Situation A: Split by '/' and normalize each part
            parts = cleaned.split('/')
            normalized_parts = []
            for part in parts:
                normalized_part = normalize_text(part)
                if normalized_part:
                    normalized_parts.append(normalized_part)
            return normalized_parts
            
    # Situation B or no slash: Keep intact
    return [cleaned]

def normalize_text_retry(text: str) -> str:
    """
    More aggressive normalization for the Retry layer (e.g. removing parenthetical
    elements at the end, stripping quotes, and reapplying standard cleaning).
    """
    cleaned = normalize_text(text)
    
    # Remove parenthetical info at the end, e.g. "apple (noun)" or "apple [adj.]"
    cleaned = re.sub(r'\s*\([^)]*\)\s*$', '', cleaned)
    cleaned = re.sub(r'\s*\[[^\]]*\]\s*$', '', cleaned)
    
    # Remove leading/trailing quote characters
    cleaned = re.sub(r'^["\'“‘]+|["\'”’]+$', '', cleaned)
    
    return normalize_text(cleaned)

def normalize_for_ai_retry(raw_text: str) -> list[str]:
    """
    Applies aggressive normalization and slash-splitting for the Retry flow.
    """
    cleaned = normalize_text_retry(raw_text)
    if not cleaned:
        return []
        
    if '/' in cleaned:
        if not any(c.isspace() for c in cleaned):
            parts = cleaned.split('/')
            normalized_parts = []
            for part in parts:
                normalized_part = normalize_text_retry(part)
                if normalized_part:
                    normalized_parts.append(normalized_part)
            return normalized_parts
            
    return [cleaned]
