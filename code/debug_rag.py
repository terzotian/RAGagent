import os
import asyncio
from backend.model.agent_router import _classify_intent_ollama
from backend.model.embedding import get_embedding
from backend.model.vector_store import query_documents

async def debug():
    query = "How can I pay my tuition fee?"
    print(f"DEBUG: Testing query: '{query}'")

    # 1. Test Intent Classification
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_GEN_MODEL", "qwen3:8b")
    language = "en"

    print("DEBUG: Testing Intent Classification...")
    intent = _classify_intent_ollama(query, base_url, model, language)
    print(f"DEBUG: Intent result: {intent}")

    if intent != "PRIVATE":
        print("CRITICAL WARNING: Intent classified as GENERAL. Retrieval will be skipped!")

    # 2. Test Vector Retrieval
    print("\nDEBUG: Testing Vector Retrieval...")
    vec = get_embedding(query)
    if not vec:
        print("CRITICAL ERROR: Failed to get embedding from Ollama.")
        return

    print(f"DEBUG: Embedding generated (len={len(vec)}). Querying ChromaDB 'public' collection...")

    results = query_documents("public", [vec], n_results=5)

    if not results or not results['documents']:
        print("CRITICAL ERROR: No documents returned from ChromaDB.")
    else:
        docs = results['documents'][0]
        distances = results['distances'][0]
        metas = results['metadatas'][0]

        print(f"DEBUG: Found {len(docs)} documents.")
        for i in range(len(docs)):
            dist = distances[i]
            score = 1 / (1 + dist)
            print(f"--- Result {i+1} ---")
            print(f"Source: {metas[i].get('source')}")
            print(f"Distance: {dist}")
            print(f"Calculated Score: {score}")
            print(f"Content Preview: {docs[i][:100]}...")

if __name__ == "__main__":
    asyncio.run(debug())
