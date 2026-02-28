import os
import sys
import asyncio
from sqlalchemy import text
from sqlalchemy.orm import Session

# Add project root
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)
sys.path.append(os.path.join(root_dir, "code"))

from backend.database.connection import SessionLocal, engine
from backend.database.models import DBItem
from backend.model.llm_service import LLMService

async def verify_rag():
    print("--- Verifying RAG Status ---")

    # 1. Check DB Connection and Item Count
    db = SessionLocal()
    try:
        count = db.query(DBItem).count()
        print(f"Total Vector Items in DB: {count}")

        if count == 0:
            print("ERROR: No items found in DB. Reindexing might have failed.")
            return

        # 2. Check Embedding Dimension
        first_item = db.query(DBItem).first()
        if first_item is not None and first_item.embedding is not None:
            dim = len(first_item.embedding)
            print(f"Embedding Dimension: {dim}")
            if dim == 768:
                print("SUCCESS: Dimension is 768 (Vertex AI Compatible)")
            else:
                print(f"WARNING: Dimension is {dim}, expected 768")

        # 3. Test Vector Search
        print("\n--- Testing Vector Search (Vertex AI + pgvector) ---")
        query = "How to apply for scholarship?"

        llm = LLMService()
        # Ensure we use Vertex AI
        print("Generating embedding for query...")
        query_vec = llm.get_embedding(query, model="text-embedding-004", provider="vertex")

        if not query_vec:
            print("ERROR: Failed to generate embedding from Vertex AI. Trying fallback...")
            query_vec = llm.get_embedding(query, model="text-embedding-004", provider="auto")

        if query_vec:
            print(f"Query embedding generated (dim={len(query_vec)})")

            # Perform search using raw SQL for pgvector
            # distance_cosine or <=> operator
            sql = text("""
                SELECT document, metadata_, 1 - (embedding <=> :query_vec) as similarity
                FROM items
                ORDER BY embedding <=> :query_vec
                LIMIT 3
            """)

            results = db.execute(sql, {"query_vec": str(query_vec)}).fetchall()

            print(f"\nTop 3 Results for '{query}':")
            for i, row in enumerate(results):
                doc_preview = row[0][:100].replace("\n", " ")
                print(f"{i+1}. [Score: {row[2]:.4f}] {doc_preview}...")
                print(f"   Source: {row[1].get('original_file', 'Unknown')}")
        else:
            print("CRITICAL: Could not generate embedding for query.")

    except Exception as e:
        print(f"ERROR during verification: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(verify_rag())
