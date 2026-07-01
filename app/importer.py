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

def extract_words_from_docx(file_path: str) -> list[str]:
    """
    Reads a .docx file line-by-line (from paragraphs and tables), cleans each line,
    and extracts English words/phrases in their original order without duplicates.
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
                cleaned_terms.append(cleaned)
                
    # Lowercase and deduplicate while preserving the original order of appearance
    unique_terms = list(dict.fromkeys(t.lower() for t in cleaned_terms))
    return unique_terms
