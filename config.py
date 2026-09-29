import os
from dotenv import load_dotenv

load_dotenv()

# LLM settings
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

# Embedding settings
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Retrieval settings
TOP_K = 4
DISTANCE_THRESHOLD = 0.65

# Chunking settings
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150

# Storage
CHROMA_PERSIST_DIR = "./chroma_store"
COLLECTION_NAME = "enterprise_docs"