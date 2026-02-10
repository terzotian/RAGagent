import os
import asyncio
from backend.root_path import POLICIES_DIR, PIECES_DIR
from backend.model.rag_indexer import ingest_file

async def reindex_public():
    print(f"Reindexing public policies from {POLICIES_DIR} to {PIECES_DIR}")

    if not os.path.exists(POLICIES_DIR):
        print(f"Error: Policies directory not found: {POLICIES_DIR}")
        return

    files = [f for f in os.listdir(POLICIES_DIR) if f != ".DS_Store"]
    print(f"Found {len(files)} files.")

    for f in files:
        file_path = os.path.join(POLICIES_DIR, f)
        # Use 'public' as base name, matching main.py accessible_bases
        await ingest_file("public", file_path)

if __name__ == "__main__":
    asyncio.run(reindex_public())
