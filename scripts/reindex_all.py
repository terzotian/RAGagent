import os
import sys
import glob
import asyncio
import logging

# Add project root and code directory to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)
sys.path.append(os.path.join(root_dir, "code"))

from backend.model.rag_indexer import ingest_file
from backend.database.connection import SessionLocal, engine
from backend.database.models import Base
from backend.root_path import KB_ROOT

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def reindex_all_files():
    """
    Scans the knowledge_base directory and re-indexes all files into the new pgvector database.
    """
    logger.info("Starting re-indexing process...")

    # Ensure tables are created in the new database
    logger.info("Ensuring database tables exist...")
    Base.metadata.create_all(bind=engine)

    # Path to knowledge base (runtime data under .local_data)
    kb_path = KB_ROOT

    if not os.path.exists(kb_path):
        logger.error(f"Knowledge base directory not found at: {kb_path}")
        return

    # In our project, files are usually in backend/knowledge_base/{base}/
    # We should find all directories in kb_path and treat them as bases
    bases = [d for d in os.listdir(kb_path) if os.path.isdir(os.path.join(kb_path, d))]

    total_files = 0
    success_count = 0
    fail_count = 0

    for base in bases:
        base_dir = os.path.join(kb_path, base)
        # Find all files in the base directory (excluding 'pieces' directory if it exists)
        files = []
        for root, dirs, filenames in os.walk(base_dir):
            if 'pieces' in dirs:
                dirs.remove('pieces') # Don't re-index pieces
            for f in filenames:
                if f.endswith(('.pdf', '.pptx', '.txt', '.md', '.docx', '.doc')):
                    files.append(os.path.join(root, f))

        logger.info(f"Found {len(files)} files in base '{base}'")
        total_files += len(files)

        for file_path in files:
            try:
                logger.info(f"Indexing [{base}]: {os.path.basename(file_path)}")
                await ingest_file(base, file_path)
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to index {file_path}: {e}")
                fail_count += 1

    logger.info(f"Re-indexing complete. Success: {success_count}, Fail: {fail_count}, Total: {total_files}")

if __name__ == "__main__":
    asyncio.run(reindex_all_files())
