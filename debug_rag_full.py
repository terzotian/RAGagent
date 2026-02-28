import os
import sys
import asyncio
import json

# Add current directory to sys.path to ensure backend modules can be imported
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(root_dir)
sys.path.append(os.path.join(root_dir, "code"))

from backend.model.embedding import get_embedding
from backend.model.vector_store import query_documents
from backend.model.doc_search import search_documents, load_segments_from_folder
from backend.root_path import piece_dir

async def debug_full():
    query = "How can I pay my tuition fee?"
    print(f"DEBUG: Testing query: '{query}'")

    # 1. Test Vector Retrieval (pgvector)
    print("\n--- Testing Vector Retrieval (pgvector) ---")
    vec = get_embedding(query, model="bge-m3")
    if not vec:
        print("Warning: Failed to get embedding from Ollama (bge-m3). Trying nomic-embed-text...")
        vec = get_embedding(query, model="nomic-embed-text")

    if not vec:
        print("CRITICAL ERROR: Failed to get embedding from Ollama.")
    else:
        print(f"Embedding generated (len={len(vec)}). Querying pgvector 'public' collection...")
        results = query_documents("public", [vec], n_results=3)
        if not results or not results.get('documents'):
            print("No documents returned from pgvector.")
        else:
            docs = results.get('documents', [[]])[0]
            metas = results.get('metadatas', [[]])[0]
            distances = results.get('distances', [[]])[0]
            print(f"Found {len(docs)} documents.")
            for i in range(len(docs)):
                print(f"  [Vector Result {i+1}] Score: {1-distances[i]:.4f} | Source: {metas[i].get('source', 'Unknown')}")

    # 2. Test TF-IDF Retrieval (Local Files)
    print("\n--- Testing TF-IDF Retrieval (Local Files) ---")
    base = "public"
    p_dir = piece_dir(base)
    print(f"Loading segments from: {p_dir}")

    if not os.path.exists(p_dir):
         print(f"CRITICAL ERROR: Pieces directory not found: {p_dir}")
    else:
        # Load segments
        # Note: load_segments_from_folder returns a list of dicts {'content': ..., 'source': ...}
        segments = []
        try:
            # We need to manually walk and load because load_segments_from_folder iterates
            # over the folder given.
            # Let's use the function from doc_search if it works recursively or for file list
            segments = load_segments_from_folder(p_dir)
            print(f"Loaded {len(segments)} segments.")

            if len(segments) > 0:
                # Perform search
                # search_documents is async
                tfidf_results = await search_documents(query, segments, top_k=3)
                print(f"Found {len(tfidf_results)} TF-IDF matches.")
                for i, res in enumerate(tfidf_results):
                     # search_documents returns list of tuples or dicts?
                     # Checking doc_search.py: returns list of indices?
                     # Wait, let's check doc_search.py again.
                     # It returns 'results' which is a list.
                     # But the snippet I read was truncated or didn't show the return construction fully.
                     # Let's assume it returns a list of dicts with 'content', 'source', 'similarity' based on common pattern.
                     # I'll print the raw result first to be safe.
                     print(f"  [TF-IDF Result {i+1}] {res}")
            else:
                print("No segments found to search.")

        except Exception as e:
            print(f"Error during TF-IDF search: {e}")

if __name__ == "__main__":
    asyncio.run(debug_full())
