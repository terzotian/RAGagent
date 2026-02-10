import os
import json
import time
import requests
import asyncio
from typing import List, Dict, Tuple, Any
from backend.model.ques_assemble import generate_search_query
from backend.model.doc_search import search_documents, load_segments_from_folder
# from backend.model.lightrag_search import search_documents_lightrag
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
    prompt_cn = "请判断这个问题是否需要查询学校内部政策、课程资料或作业文档。如果是，请务必回答 PRIVATE；如果是普通闲聊或通用知识，回答 GENERAL。只回答一个词。"
    prompt_en = "Determine if this question requires retrieving internal university policies, courses, or assignments. If yes, reply PRIVATE. If it is chitchat or general knowledge, reply GENERAL. Reply with ONE WORD only."
    prompt = prompt_cn if language.lower().startswith("zh") else prompt_en
    data = {"model": model, "prompt": f"{prompt}\nQuestion: {query}\nAnswer:", "stream": False}
    try:
        r = requests.post(f"{base_url}/api/generate", json=data, timeout=20)
        if r.status_code == 200:
            try:
                obj = r.json()
                txt = obj.get("response", "").strip().upper()
            except:
                txt = r.text.strip().upper()

            # 只要包含 PRIVATE 就优先认为是 PRIVATE
            if "PRIVATE" in txt:
                return "PRIVATE"
            # 只有明确说 GENERAL 且不含 PRIVATE 才算 GENERAL
            if "GENERAL" in txt:
                return "GENERAL"
    except:
        pass
    # 默认倾向于检索，避免漏掉信息
    return "PRIVATE"

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

    # 1. 优先进行意图识别 (Prioritize Intent Classification)
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_GEN_MODEL", "qwen3:8b")

    # 快速检查是否为闲聊 (Quick check for chitchat)
    # 只有当问题非常短或者明显是打招呼时，才跳过检索?
    # 为了稳妥，我们先做意图识别。
    intent = await asyncio.to_thread(_classify_intent_ollama, current_question, base_url, model, language)

    if intent == "GENERAL":
        print(f"DEBUG: Intent is GENERAL. Skipping retrieval.")
        prompt_cn = "请直接回答用户的问题："
        prompt_en = "Answer the user's question directly:"
        prompt = prompt_cn if language.lower().startswith("zh") else prompt_en
        gen = _ollama_stream(f"{prompt}\n{current_question}", base_url, model)
        return gen, []

    # 2. 如果是 PRIVATE，则进行检索 (If PRIVATE, proceed to retrieval)
    print(f"DEBUG: Intent is PRIVATE. Starting retrieval.")

    try:
        search_query, assembled_question, generate_time = await generate_search_query(current_question, previous_questions)
    except:
        search_query = current_question
        assembled_question = current_question
        generate_time = 0.0

    # 检索相关文档
    # 使用传统检索
    use_lightrag = False

    # 聚合检索结果
    references = []
    search_time = 0.0

    # 确保 bases 列表唯一
    unique_bases = list(set(bases))
    print(f"DEBUG: Searching across bases: {unique_bases}")

    try:
        # 传统检索 (按顺序)
        for base in unique_bases:
            # 确保 piece_dir 正确指向存储切片的目录
            input_folder = piece_dir(base=base)
            if os.path.exists(input_folder):
                refs, t = await search_documents(search_query, load_segments_from_folder(input_folder=input_folder))
                for ref in refs:
                    if "source" in ref and "file_name" not in ref:
                        ref["file_name"] = ref["source"]
                references.extend(refs)
                search_time += t
            else:
                print(f"DEBUG: Base directory not found: {input_folder}")
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

    threshold = float(os.getenv("SIMILARITY_THRESHOLD", "0.01"))
    max_score = 0.0
    for ref in references:
        if "similarity" in ref:
            max_score = max(max_score, _parse_similarity(ref["similarity"]))

    print(f"DEBUG: Max score: {max_score}, Threshold: {threshold}, References count: {len(references)}")

    # 3. 如果有高分结果，或者 intent 是 PRIVATE (即使用户认为它是private，但没搜到，我们也可以尝试用 RAG 风格回答，或者告诉用户没找到)
    # 这里的逻辑是：如果搜到了，就用 RAG。
    if max_score >= threshold and len(references) > 0:
        print("DEBUG: Entering RAG mode")
        gen = stream_answer(assembled_question, generate_time, references, search_time, target_language=language)
        return gen, references

    # 4. 如果搜不到结果 (Failover)
    # 之前是再次检查 intent。现在我们已经检查过了，是 PRIVATE。
    # 如果是 PRIVATE 但没搜到，说明知识库里没有。
    # 这时候应该告诉用户“找不到相关信息”，或者尝试用通用知识回答但标注“未找到引用”。
    # 为了保持用户体验（就像用户说的“之前问学校相关的也会直接给”），如果搜不到，我们可以尝试直接回答。

    print(f"DEBUG: No relevant docs found (max_score={max_score}). Fallback to direct answer.")
    prompt_cn = "并未在知识库中找到相关文档，请尝试利用你的通用知识回答（请告知用户未找到校内信息，请不要编造）："
    prompt_en = "No relevant documents found in knowledge base. Please answer using general knowledge (warn user no internal info found):"
    prompt = prompt_cn if language.lower().startswith("zh") else prompt_en
    # Use await for stream wrapper if needed, but _ollama_stream is async gen, so just calling it is fine.
    # But wait, did we use model from env? Yes.
    gen = _ollama_stream(f"{prompt}\n{current_question}", base_url, model)
    return gen, []
