import os
import sys
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

async def test_reindex_one_file():
    logger.info("Starting test re-indexing process...")

    # Ensure tables are created
    Base.metadata.create_all(bind=engine)

    # Pick one file
    # backend/knowledge_base/public/policies/Admission Requirements.docx
    file_path = os.path.join(KB_ROOT, "public", "policies", "Admission Requirements.docx")

    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return

    try:
        logger.info(f"Indexing: {file_path}")
        await ingest_file("public", file_path)
        logger.info("Successfully indexed file.")
    except Exception as e:
        logger.error(f"Failed to index {file_path}: {e}")

if __name__ == "__main__":
    asyncio.run(test_reindex_one_file())
