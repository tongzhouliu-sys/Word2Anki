import re
import docx
from pathlib import Path

def clean_line(line: str) -> str | None:
    """
    Cleans a line of text: removes list numbering/bullets, strips whitespace,
    and validates that the line contains an English word or phrase.
    """
    line = line.strip()
    if not line:
        return None

    # Remove list prefixes like "1. ", "2) ", "- ", "* ", "• "
    line = re.sub(r'^\s*(\d+[\.\)]|[\-\*•])\s*', '', line).strip()
    
    # Must contain at least one English letter and only consist of valid English word/phrase characters
    if re.search(r'[a-zA-Z]', line) and re.match(r'^[a-zA-Z\s\-\'\,\.\(\)\?\/]+$', line):
        return line
    return None

def normalize_term(line: str) -> list[str]:
    """
    Normalizes a line containing slashes into a list of separate words or phrases.
    Handles synonyms (e.g. "servant/butler"), phrase options (e.g. "to stifle a yawn/cough/scream"),
    and embedded options (e.g. "keep a straight/poker face").
    """
    line = line.strip()
    if "/" not in line:
        return [line]

    # 1. If there are spaces around any slash (e.g. "a / b" or "a/ b"),
    # it's a list of independent synonyms. We split by slash and return the parts.
    if " /" in line or "/ " in line:
        parts = [p.strip() for p in line.split('/') if p.strip()]
        return parts

    # 2. Check for Phrase Prefix Rule:
    # e.g., "to stifle a yawn/cough/scream" -> ["to stifle a yawn", "cough", "scream"]
    parts = [p.strip() for p in line.split('/') if p.strip()]
    if len(parts) > 1:
        words_in_first = parts[0].split()
        if len(words_in_first) >= 2 and all(len(p.split()) == 1 for p in parts[1:]):
            prefix = " ".join(words_in_first[:-1])
            expanded = []
            for p in parts:
                if p.startswith(prefix + " "):
                    expanded.append(p)
                else:
                    expanded.append(f"{prefix} {p}")
            return expanded

    # 3. Check for Embedded Token Rule (e.g., "keep a straight/poker face")
    tokens = line.split()
    slash_token_idx = -1
    for idx, token in enumerate(tokens):
        if '/' in token and not token.startswith('/') and not token.endswith('/'):
            slash_token_idx = idx
            break

    if slash_token_idx != -1:
        target_token = tokens[slash_token_idx]
        options = [opt.strip() for opt in target_token.split('/') if opt.strip()]
        expanded = []
        for opt in options:
            new_tokens = list(tokens)
            new_tokens[slash_token_idx] = opt
            expanded.append(" ".join(new_tokens))
        return expanded

    # 4. Fallback: just return the split parts
    return parts

def extract_words_from_docx(file_path: str) -> list[str]:
    """
    Reads a .docx file line-by-line (from paragraphs and tables), cleans each line,
    normalizes slash-expressions, and extracts English words/phrases in their
    original order without duplicates.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Word document not found at: {file_path}")

    doc = docx.Document(str(path))
    raw_lines = []
    
    # Extract from paragraphs
    for para in doc.paragraphs:
        if para.text:
            raw_lines.append(para.text)
            
    # Extract from tables
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text:
                    raw_lines.append(cell.text)
                    
    cleaned_terms = []
    for line in raw_lines:
        # Split by newline in case a cell or paragraph has multiple lines
        for sub_line in line.split('\n'):
            cleaned = clean_line(sub_line)
            if cleaned:
                # Normalize and expand any slash terms
                normalized_terms = normalize_term(cleaned)
                for term in normalized_terms:
                    cleaned_term = clean_line(term)
                    if cleaned_term:
                        cleaned_terms.append(cleaned_term)
                
    # Lowercase and deduplicate while preserving the original order of appearance
    unique_terms = list(dict.fromkeys(t.lower() for t in cleaned_terms))
    return unique_terms
