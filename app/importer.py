import re
import docx
from pathlib import Path

def extract_words_from_docx(file_path: str) -> list[str]:
    """
    Reads a .docx file and extracts all unique English words containing at least 2 characters,
    converted to lowercase.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Word document not found at: {file_path}")

    doc = docx.Document(str(path))
    full_text = []
    
    # Extract from paragraphs
    for para in doc.paragraphs:
        if para.text:
            full_text.append(para.text)
            
    # Extract from tables
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text:
                    full_text.append(cell.text)
                    
    text = "\n".join(full_text)
    
    # Extract English words (at least 2 letters)
    words = re.findall(r'\b[a-zA-Z]{2,}\b', text)
    
    # Lowercase and deduplicate while preserving the original order of appearance
    unique_words = list(dict.fromkeys(w.lower() for w in words))
    return unique_words
