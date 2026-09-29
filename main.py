import os
import shutil
import time

from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel

from ingestion import build_chunk_records
from vector_store import add_chunks, query, list_documents, delete_document
from llm import generate_answer

app = FastAPI(title="Enterprise Document Q&A Assistant")

UPLOAD_DIR = "./uploaded_docs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

QA_LOG: list[dict] = []


class AskRequest(BaseModel):
    question: str


@app.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    safe_name = os.path.basename(file.filename or "")
    if not safe_name.lower().endswith((".pdf", ".txt")):
        return {"error": "Only PDF and TXT documents are supported."}

    save_path = os.path.join(UPLOAD_DIR, safe_name)
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    records = build_chunk_records(save_path, doc_name=safe_name)
    num_chunks = add_chunks(records)

    return {"doc_name": safe_name, "chunks_indexed": num_chunks}


@app.post("/ask")
async def ask(req: AskRequest):
    start = time.time()
    chunks, is_confident = query(req.question)

    if not is_confident:
        answer = "I don't have enough information in the indexed documents to answer that."
        sources = []
    else:
        answer = generate_answer(req.question, chunks)
        sources = [
            {"doc_name": c["doc_name"], "chunk_index": c["chunk_index"]}
            for c in chunks
        ]

    result = {
        "question": req.question,
        "answer": answer,
        "sources": sources,
        "answered": is_confident,
        "latency_seconds": round(time.time() - start, 2),
    }
    QA_LOG.append(result)
    return result


@app.get("/documents")
async def documents():
    return {"documents": list_documents()}


@app.delete("/documents/{doc_name}")
async def remove_document(doc_name: str):
    delete_document(doc_name)
    return {"deleted": doc_name}


@app.get("/eval-log")
async def eval_log():
    return {"log": QA_LOG}


@app.get("/health")
async def health():
    return {"status": "ok"}