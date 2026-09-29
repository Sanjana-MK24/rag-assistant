from openai import OpenAI
from config import GROQ_API_KEY, LLM_MODEL

_client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)

SYSTEM_PROMPT = """You are an enterprise document assistant. Answer the user's \
question using ONLY the context provided below.

Rules:
- If the context does not contain enough information to answer, say clearly: \
"I don't have enough information in the indexed documents to answer that."
- Do not use outside knowledge or make assumptions beyond the context.
- Keep answers concise (2-5 sentences unless the question needs more detail).
- Do not fabricate document names, numbers, or facts not present in the context.
"""


def generate_answer(question: str, chunks: list[dict]) -> str:
    if not chunks:
        return "I don't have enough information in the indexed documents to answer that."

    context = "\n\n".join(
        f"[Source: {c['doc_name']}, section {c['chunk_index']}]\n{c['text']}"
        for c in chunks
    )

    user_prompt = f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"

    if not GROQ_API_KEY:
        return f"Based on the indexed documents: {chunks[0]['text'].strip()}"

    try:
        response = _client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        answer = response.choices[0].message.content
        return answer.strip() if answer else f"Based on the indexed documents: {chunks[0]['text'].strip()}"
    except Exception:
        return f"Based on the indexed documents: {chunks[0]['text'].strip()}"


# --- Quick test when you run this file directly ---
if __name__ == "__main__":
    from vector_store import query

    question = "How many days of annual leave do employees get?"
    chunks, confident = query(question)

    if confident:
        answer = generate_answer(question, chunks)
        print("Question:", question)
        print("Answer:", answer)
    else:
        print("Not confident enough to answer.")