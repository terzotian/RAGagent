import os
import asyncio
import json
import requests
from pathlib import Path
from typing import List

def _ollama_generate(prompt: str, base_url: str, model: str) -> str:
    try:
        r = requests.post(f"{base_url}/api/generate", json={"model": model, "prompt": prompt, "stream": False}, timeout=120)
        if r.status_code == 200:
            try:
                obj = r.json()
                return obj.get("response", "")
            except:
                txt = r.text
                return txt
    except:
        return ""
    return ""

def _ollama_embed(texts: List[str], base_url: str, model: str) -> List[List[float]]:
    vecs = []
    for t in texts:
        try:
            r = requests.post(f"{base_url}/api/embeddings", json={"model": model, "prompt": t}, timeout=60)
            if r.status_code == 200:
                obj = r.json()
                v = obj.get("embedding")
                if isinstance(v, list):
                    vecs.append(v)
                else:
                    vecs.append([])
            else:
                vecs.append([])
        except:
            vecs.append([])
    return vecs

async def ingest_file(base: str, file_path: str):
    from raganything.raganything import RAGAnything
    from raganything.config import RAGAnythingConfig
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    gen_model = os.getenv("OLLAMA_GEN_MODEL", "qwen2.5:3b")
    embed_model = os.getenv("OLLAMA_EMB_MODEL", "bge-m3")
    working_root = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))) / "backend" / "knowledge_base" / base / "rag_storage"
    output_dir = str(Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))) / "backend" / "knowledge_base" / base / "rag_output")
    cfg = RAGAnythingConfig()
    cfg.working_dir = str(working_root)
    cfg.parser_output_dir = output_dir
    inst = RAGAnything(
        llm_model_func=lambda prompt, **kwargs: _ollama_generate(prompt, base_url, gen_model),
        embedding_func=lambda texts, **kwargs: _ollama_embed(texts, base_url, embed_model),
        config=cfg,
    )
    await inst.process_document_complete(file_path=file_path)
