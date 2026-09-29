from pypdf import PdfReader
from config import CHUNK_SIZE, CHUNK_OVERLAP

SUPPORTED_EXTENSIONS = {".pdf", ".txt"}


def extract_text(file_path: str) -> str:
    """Read raw text out of a .pdf or .txt file."""
    extension = "." + file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError("Only PDF and TXT documents are supported.")

    if extension == ".pdf":
        reader = PdfReader(file_path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
    """Split text into overlapping chunks."""
    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def build_chunk_records(file_path: str, doc_name: str):
    """Turn a document into a list of chunk records with metadata."""
    text = extract_text(file_path)
    chunks = chunk_text(text)
    return [
        {"text": c, "doc_name": doc_name, "chunk_index": i}
        for i, c in enumerate(chunks)
    ]


# --- Quick test when you run this file directly ---
if __name__ == "__main__":
    records = build_chunk_records("sample_docs/leave_policy.txt", "leave_policy.txt")
    print(f"Got {len(records)} chunks\n")
    print("First chunk:")
    print(records[0])