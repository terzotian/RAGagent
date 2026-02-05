import os
import time
from typing import List, Tuple
from pathlib import Path
import requests

from backend.model.doc_search import search_documents, load_segments_from_folder
from backend.root_path import piece_dir

def _ollama_embed(texts: List[str], base_url: str, model: str) -> List[List[float]]:
    vecs = []
    for t in texts:
        try:
            r = requests.post(f"{base_url}/api/embeddings", json={"model": model, "prompt": t}, timeout=30)
            if r.status_code == 200:
                obj = r.json()
                v = obj.get("embedding")
                vecs.append(v if isinstance(v, list) else [])
            else:
                vecs.append([])
        except:
            vecs.append([])
    return vecs

async def search_documents_lightrag(search_query: str, base: str, top_k: int = 5) -> Tuple[List[dict], float]:
    start_search = time.time()
    try:
        from raganything.raganything import RAGAnything
        from raganything.config import RAGAnythingConfig
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        embed_model = os.getenv("OLLAMA_EMB_MODEL", "bge-m3")
        cfg = RAGAnythingConfig()
        cfg.working_dir = str(Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))) / "backend" / "knowledge_base" / base / "rag_storage")
        inst = RAGAnything(
            llm_model_func=lambda prompt, **kwargs: "",
            embedding_func=lambda texts, **kwargs: _ollama_embed(texts, base_url, embed_model),
            config=cfg,
        )
        try:
            await inst._ensure_lightrag_initialized()
        except:
            pass
        vdb = getattr(inst.lightrag, "chunks_vdb", None)
        results = []
        if vdb is not None:
            for m in ["search", "similarity_search", "query", "knn_search", "retrieve"]:
                fn = getattr(vdb, m, None)
                if callable(fn):
                    try:
                        out = await fn(search_query, top_k=top_k)
                        # normalize outputs -> list of dicts with content, file_path, score
                        if isinstance(out, list):
                            for item in out:
                                if isinstance(item, dict):
                                    content = item.get("content") or item.get("text") or ""
                                    file_path = item.get("file_path") or item.get("source") or ""
                                    score = item.get("score") or item.get("similarity") or 0.7
                                    if file_path:
                                        results.append({
                                            "content": str(content),
                                            "file_name": str(file_path),
                                            "similarity": f"{float(score)*100:.1f}%"
                                        })
                            break
                    except:
                        continue
        if results:
            return results, time.time() - start_search
    except:
        pass
    # fallback to TF-IDF pieces
    refs, _ = await search_documents(search_query, load_segments_from_folder(input_folder=piece_dir(base=base)), top_k=top_k)
    for r in refs:
        if "source" in r and "file_name" not in r:
            r["file_name"] = r["source"]
    return refs, time.time() - start_search
