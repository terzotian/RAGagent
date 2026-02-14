import chromadb
from chromadb.config import Settings
import os

# Global client instance
_client = None

def get_client():
    global _client
    if _client is None:
        # Store data in AgenticRAG/data/chroma_db
        # Assuming this file is in backend/model/vector_store.py
        # root is ../../..
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        db_path = os.path.join(root_dir, "data", "chroma_db")
        os.makedirs(db_path, exist_ok=True)
        print(f"DEBUG: Initializing ChromaDB at {db_path}")
        try:
            _client = chromadb.PersistentClient(path=db_path)
        except Exception as e:
            print(f"Error initializing ChromaDB: {e}")
            raise e
    return _client

def get_collection(name: str):
    """
    Get or create a collection.
    name: usually the 'base' name (e.g., 'public', 'course_XYZ')
    """
    client = get_client()
    return client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})

def add_documents(collection_name: str, documents: list, metadatas: list, ids: list, embeddings: list):
    """
    Add documents with pre-computed embeddings.
    """
    if not documents:
        return

    collection = get_collection(collection_name)
    try:
        collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        print(f"DEBUG: Added {len(documents)} docs to Chroma collection '{collection_name}'")
    except Exception as e:
        print(f"Error adding to ChromaDB: {e}")

def query_documents(collection_name: str, query_embeddings: list, n_results: int = 5):
    """
    Query documents using embeddings.
    """
    try:
        collection = get_collection(collection_name)
        # Check if collection is empty
        if collection.count() == 0:
            return None

        results = collection.query(
            query_embeddings=query_embeddings,
            n_results=n_results
        )
        return results
    except Exception as e:
        print(f"Error querying ChromaDB: {e}")
        return None
