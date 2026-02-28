import os
import sys
import asyncio

# Add current directory to sys.path to ensure backend modules can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.model.embedding import get_embedding
from backend.model.vector_store import query_documents
from backend.model.agent_router import _planner_agent

async def debug():
    query = "How can I pay my tuition fee?"
    print(f"DEBUG: Testing query: '{query}'")

    # 1. Test Intent Classification
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_GEN_MODEL", "qwen3:8b")
    language = "en"

    print("DEBUG: Testing Master Planner...")
    plan = await _planner_agent(query, base_url, model, language, conversation_history=None)
    print(f"DEBUG: Plan: {plan}")
    print(f"DEBUG: Intent result: {intent}")

    if intent != "PRIVATE" and intent != "POLICY": # POLICY is also a valid intent for retrieval
         # Note: _classify_intent_ollama returns PRIVATE or GENERAL.
         # _classify_private_type_ollama returns COURSE/STUDENT/POLICY.
         # But here we only call intent classification.
         pass

    # 2. Test Vector Retrieval
    print("\nDEBUG: Testing Vector Retrieval (pgvector)...")
    # Use Vertex embedding if available, otherwise fallback to Ollama nomic-embed-text
    vec = get_embedding(query, model="text-embedding-004")

    if not vec:
        print("CRITICAL ERROR: Failed to get embedding from Ollama.")
        return

    print(f"DEBUG: Embedding generated (len={len(vec)}). Querying pgvector 'public' collection...")

    results = query_documents("public", [vec], n_results=5)

    if not results:
        print("CRITICAL ERROR: No documents returned from pgvector.")
    else:
        # Check structure of results from pgvector implementation
        # The implementation returns a list of Row objects or similar if not formatted exactly like Chroma
        # query_documents in vector_store.py returns:
        # { 'ids': [...], 'distances': [...], 'metadatas': [...], 'documents': [...] }

        docs = results.get('documents', [[]])[0]
        distances = results.get('distances', [[]])[0]
        metas = results.get('metadatas', [[]])[0]

        print(f"DEBUG: Found {len(docs)} documents.")
        for i in range(len(docs)):
            dist = distances[i]
            # Cosine distance: 0 is identical, 1 is opposite (for normalized vectors)
            # Similarity = 1 - distance
            score = 1 - dist
            print(f"--- Result {i+1} ---")
            print(f"Source: {metas[i].get('source', 'Unknown')}")
            print(f"Distance: {dist}")
            print(f"Calculated Score: {score}")
            print(f"Content Preview: {docs[i][:100]}...")

if __name__ == "__main__":
    asyncio.run(debug())
