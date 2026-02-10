import os
import json
import time
import requests
import asyncio
from typing import List, Dict, Tuple, Any
from backend.model.ques_assemble import generate_search_query
from backend.model.doc_search import search_documents, load_segments_from_folder
from backend.model.lightrag_search import search_documents_lightrag
from backend.root_path import piece_dir
from backend.model.rag_stream import stream_answer

def _parse_similarity(s: Any) -> float:
    try:
        if isinstance(s, str) and s.endswith("%"):
            return float(s.rstrip("%")) / 100.0
        return float(s)
    except:
        return 0.0

def _classify_intent_ollama(query: str, base_url: str, model: str, language: str) -> str:
    prompt_cn = "请判断这个问题是否针对私有数据或内部文档，若是回答 PRIVATE，否则回答 GENERAL："
    prompt_en = "Decide if the question targets private data or internal docs. Reply PRIVATE or GENERAL:"
    prompt = prompt_cn if language.lower().startswith("zh") else prompt_en
    data = {"model": model, "prompt": f"{prompt}\n{query}", "stream": False}
    try:
        r = requests.post(f"{base_url}/api/generate", json=data, timeout=20)
        if r.status_code == 200:
            try:
                obj = r.json()
                txt = obj.get("response", "").strip().upper()
            except:
                txt = r.text.strip().upper()
            if "PRIVATE" in txt and "GENERAL" not in txt:
                return "PRIVATE"
            if "GENERAL" in txt and "PRIVATE" not in txt:
                return "GENERAL"
    except:
        pass
    return "GENERAL"

async def _ollama_stream(prompt: str, base_url: str, model: str):
    try:
        with requests.post(f"{base_url}/api/generate", json={"model": model, "prompt": prompt, "stream": True}, stream=True, timeout=300) as r:
            if r.status_code != 200:
                return
            for line in r.iter_lines():
                if not line:
                    await asyncio.sleep(0)
                    continue
                try:
                    obj = json.loads(line.decode("utf-8"))
                    chunk = obj.get("response")
                    if chunk:
                        yield chunk
                except:
                    await asyncio.sleep(0)
    except:
        return

async def route_stream(current_question: str, previous_questions: List[str], language: str, bases: List[str], temp_file_content: str = None):
    start_t = time.time()
    try:
        search_query, assembled_question, generate_time = await generate_search_query(current_question, previous_questions)
    except:
        search_query = current_question
        assembled_question = current_question
        generate_time = 0.0
    # 检索相关文档
    # 默认开启 LightRAG 检索，除非环境变量明确设置为 0
    use_lightrag = os.getenv("USE_LIGHTRAG_RETRIEVAL", "1") == "1"
    if use_lightrag:
        print("Using LightRAG retrieval...")

    # 聚合检索结果
    references = []
    search_time = 0.0

    # 确保 bases 列表唯一
    unique_bases = list(set(bases))
    print(f"DEBUG: Searching across bases: {unique_bases}")

    try:
        if use_lightrag:
            # 并行检索所有库
            tasks = [search_documents_lightrag(search_query, base) for base in unique_bases]
            results_list = await asyncio.gather(*tasks)

            # 合并结果
            for res, t in results_list:
                references.extend(res)
                search_time = max(search_time, t) # 取最长耗时
        else:
            # 传统检索 (按顺序或并行，这里简化为顺序)
            for base in unique_bases:
                refs, t = await search_documents(search_query, load_segments_from_folder(input_folder=piece_dir(base=base)))
                for ref in refs:
                    if "source" in ref and "file_name" not in ref:
                        ref["file_name"] = ref["source"]
                references.extend(refs)
                search_time += t
    except Exception as e:
        print(f"Search error: {e}")
        references = []
        search_time = 0.0

    # 对合并后的 references 按相似度降序排序
    references.sort(key=lambda x: _parse_similarity(x.get("similarity", "0%")), reverse=True)
    # 截取前 5 个最相关的 (跨库去重)
    references = references[:5]

    # Add temp file content if present
    if temp_file_content:
        references.insert(0, {
            "content": temp_file_content,
            "file_name": "Uploaded Assignment/Document",
            "similarity": "100%"
        })

    threshold = float(os.getenv("SIMILARITY_THRESHOLD", "0.6"))
    max_score = 0.0
    for ref in references:
        if "similarity" in ref:
            max_score = max(max_score, _parse_similarity(ref["similarity"]))
    if max_score >= threshold and len(references) > 0:
        gen = stream_answer(assembled_question, generate_time, references, search_time, target_language=language)
        return gen, references
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_GEN_MODEL", "qwen2.5:3b")
    intent = _classify_intent_ollama(current_question, base_url, model, language)
    if intent == "GENERAL":
        prompt_cn = "请直接回答用户的问题："
        prompt_en = "Answer the user's question directly:"
        prompt = prompt_cn if language.lower().startswith("zh") else prompt_en
        gen = _ollama_stream(f"{prompt}\n{current_question}", base_url, model)
        return gen, []
    async def empty_gen():
        if False:
            yield ""
        return
    return empty_gen(), []
