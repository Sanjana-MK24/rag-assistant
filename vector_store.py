import chromadb
from chromadb.utils import embedding_functions
from config import EMBEDDING_MODEL, CHROMA_PERSIST_DIR, COLLECTION_NAME, TOP_K, DISTANCE_THRESHOLD

_embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=EMBEDDING_MODEL
)

_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
_collection = _client.get_or_create_collection(
    name=COLLECTION_NAME,
    embedding_function=_embedding_fn,
)


def add_chunks(chunk_records: list[dict]):
    """Embed and store a list of chunk records."""
    if not chunk_records:
        return 0

    for doc_name in {record["doc_name"] for record in chunk_records}:
        _collection.delete(where={"doc_name": doc_name})

    ids = [f"{r['doc_name']}::{r['chunk_index']}" for r in chunk_records]
    documents = [r["text"] for r in chunk_records]
    metadatas = [{"doc_name": r["doc_name"], "chunk_index": r["chunk_index"]} for r in chunk_records]

    _collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    return len(chunk_records)


def query(question: str, top_k: int = TOP_K, distance_threshold: float = DISTANCE_THRESHOLD):
    """Find the closest chunks to a question. Returns (chunks, is_confident)."""
    if not question or not question.strip() or _collection.count() == 0:
        return [], False

    result_count = min(max(top_k, 1), _collection.count())
    results = _collection.query(query_texts=[question], n_results=result_count)

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    dists = results.get("distances", [[]])[0]

    if not docs:
        return [], False

    chunks = [
        {"text": d, "doc_name": m["doc_name"], "chunk_index": m["chunk_index"], "distance": dist}
        for d, m, dist in zip(docs, metas, dists)
    ]

    is_confident = chunks[0]["distance"] <= distance_threshold
    return chunks, is_confident


def list_documents():
    """List all distinct document names currently indexed."""
    all_items = _collection.get()
    doc_names = {m["doc_name"] for m in all_items.get("metadatas", [])}
    return sorted(doc_names)


def document_stats():
    """Return indexed document names and chunk counts for management views."""
    all_items = _collection.get(include=["metadatas"])
    counts = {}
    for metadata in all_items.get("metadatas", []):
        if metadata:
            name = metadata["doc_name"]
            counts[name] = counts.get(name, 0) + 1
    return [{"name": name, "chunks": count, "status": "Indexed"} for name, count in sorted(counts.items())]


def delete_document(doc_name: str):
    """Remove all chunks belonging to one document."""
    _collection.delete(where={"doc_name": doc_name})


if __name__ == "__main__":
    from ingestion import build_chunk_records

    records = build_chunk_records("sample_docs/leave_policy.txt", "leave_policy.txt")
    add_chunks(records)
    print(f"Indexed {len(records)} chunks\n")

    chunks, confident = query("How many days of annual leave do employees get?")
    print(f"Relevant question -> confident={confident}, distance={chunks[0]['distance']:.3f}")

    chunks2, confident2 = query("What is the capital of France?")
    print(f"Unrelated question -> confident={confident2}, distance={chunks2[0]['distance']:.3f}")