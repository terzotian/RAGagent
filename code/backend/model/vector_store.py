import os
import uuid
import logging
from sqlalchemy.orm import Session
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from backend.database.connection import SessionLocal
from backend.database.models import DBItem

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_documents(collection_name: str, documents: list, metadatas: list, ids: list, embeddings: list):
    """
    Add documents with pre-computed embeddings to PostgreSQL using pgvector.

    Args:
        collection_name: Used as a filter in metadata (e.g., 'public', 'course_XYZ')
        documents: List of document texts
        metadatas: List of metadata dictionaries
        ids: List of unique IDs
        embeddings: List of embedding vectors
    """
    if not documents:
        return

    db: Session = SessionLocal()
    try:
        values = []
        for i in range(len(documents)):
            meta = metadatas[i] if i < len(metadatas) else {}
            meta["collection_name"] = collection_name

            item_id = ids[i] if i < len(ids) else str(uuid.uuid4())

            values.append(
                {
                    "id": item_id,
                    "embedding": embeddings[i],
                    "document": documents[i],
                    "metadata_": meta,
                }
            )

        if not values:
            return

        stmt = pg_insert(DBItem.__table__).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=[DBItem.id],
            set_={
                "embedding": stmt.excluded.embedding,
                "document": stmt.excluded.document,
                "metadata_": stmt.excluded.metadata_,
            },
        )

        db.execute(stmt)
        db.commit()
        logger.info(f"Upserted {len(values)} documents to pgvector collection '{collection_name}'")

    except Exception as e:
        logger.error(f"Error adding to pgvector: {e}")
        db.rollback()
    finally:
        db.close()

def query_documents(collection_name: str | list[str], query_embeddings: list, n_results: int = 5):
    """
    Query documents using embeddings from PostgreSQL.

    Args:
        collection_name: Filter by this collection name (str) or list of names (list[str]) in metadata
        query_embeddings: List of query vectors (currently supports single query vector for simplicity)
        n_results: Number of results to return

    Returns:
        Dict structure compatible with ChromaDB response:
        {
            'ids': [[id1, id2, ...]],
            'distances': [[dist1, dist2, ...]],
            'metadatas': [[meta1, meta2, ...]],
            'documents': [[doc1, doc2, ...]]
        }
    """
    db: Session = SessionLocal()
    try:
        # Check if query_embeddings is a list of lists or a single list
        if not query_embeddings:
            return None

        # Handle single query vector for now (common case)
        # If query_embeddings is [[...]], take first one.
        if isinstance(query_embeddings[0], list) or hasattr(query_embeddings[0], '__iter__'):
             query_vec = query_embeddings[0]
        else:
             query_vec = query_embeddings

        # Prepare collection filter
        if isinstance(collection_name, str):
            # Single collection
            filter_condition = "metadata_ ->> 'collection_name' = :coll_name"
            params = {"coll_name": collection_name, "query_vec": str(query_vec)}
        elif isinstance(collection_name, list):
            # Multiple collections (IN clause)
            if not collection_name:
                 # Empty list means search nothing? Or search everything?
                 # Let's assume search nothing to be safe, or handle as error.
                 # But if user wants to search all, they might pass None or "all".
                 # For now, return empty if list is empty.
                 return {'ids': [[]], 'distances': [[]], 'metadatas': [[]], 'documents': [[]]}

            # Create :coll_name_0, :coll_name_1, etc.
            placeholders = [f":coll_name_{i}" for i in range(len(collection_name))]
            filter_condition = f"metadata_ ->> 'collection_name' IN ({', '.join(placeholders)})"

            params = {"query_vec": str(query_vec)}
            for i, name in enumerate(collection_name):
                params[f"coll_name_{i}"] = name
        else:
            # Fallback or error
            return None

        # SQL query using pgvector's cosine distance operator (<=>)
        # We need to compute distance as well to return it.
        stmt = text(f"""
            SELECT
                id,
                embedding <=> :query_vec as distance,
                metadata_,
                document
            FROM items
            WHERE {filter_condition}
            ORDER BY embedding <=> :query_vec
            LIMIT {n_results}
        """)

        # Execute with parameters
        result_rows = db.execute(stmt, params).fetchall()

        if not result_rows:
            return {'ids': [[]], 'distances': [[]], 'metadatas': [[]], 'documents': [[]]}

        # Format results to match ChromaDB structure
        ids = []
        distances = []
        metadatas = []
        documents = []

        for row in result_rows:
            # row is tuple-like: (id, distance, metadata_, document)
            ids.append(row[0])
            distances.append(row[1])
            metadatas.append(row[2])
            documents.append(row[3])

        return {
            'ids': [ids],
            'distances': [distances],
            'metadatas': [metadatas],
            'documents': [documents]
        }

    except Exception as e:
        logger.error(f"Error querying pgvector: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db.close()


def delete_documents_for_file(collection_name: str, original_file: str) -> int:
    """Delete vectors for a given original file within a collection.

    The traditional ingestion pipeline stores:
    - ids as "{original_file}_chunk_{i}"
    - metadata_.original_file as original_file
    - metadata_.source as "{original_file}.txt"
    """
    if not collection_name or not original_file:
        return 0

    db: Session = SessionLocal()
    try:
        source = f"{original_file}.txt"
        id_prefix = f"{original_file}_chunk_%"

        stmt = text(
            """
            DELETE FROM items
            WHERE metadata_ ->> 'collection_name' = :coll
              AND (
                metadata_ ->> 'original_file' = :orig
                OR metadata_ ->> 'source' = :source
                OR id LIKE :id_prefix
              )
            """
        )
        result = db.execute(
            stmt,
            {
                "coll": collection_name,
                "orig": original_file,
                "source": source,
                "id_prefix": id_prefix,
            },
        )
        db.commit()
        return int(result.rowcount or 0)
    except Exception as e:
        logger.error(f"Error deleting vectors for collection '{collection_name}', file '{original_file}': {e}")
        db.rollback()
        return 0
    finally:
        db.close()


