import os
import json
import time
import requests
import asyncio
import re
from typing import List, Dict, Tuple, Any
from backend.model.ques_assemble import generate_search_query
from backend.model.doc_search import search_documents, load_segments_from_folder
# from backend.model.lightrag_search import search_documents_lightrag
from backend.root_path import piece_dir
from backend.model.rag_stream import stream_answer


def _merge_mode(a: str, b: str) -> str:
    if not a:
        return b or ""
    if not b or a == b:
        return a
    return "both"


def _extract_course_bases_from_question(question: str) -> List[str]:
    if not question:
        return []
    codes = set(re.findall(r"\bCDS\d{3}\b", question.upper()))
    return [f"course_{code}" for code in codes]


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
    return "PRIVATE"


def _classify_private_type_ollama(query: str, base_url: str, model: str, language: str) -> str:
    prompt_cn = "这个问题已经被判断为需要查询校内资料。请在以下类别中选择一个最合适的：COURSE（关于课程任务、项目、考试等）、STUDENT（关于某个学生自己提交的作业或表现）、POLICY（关于学费、规章制度、通用教学政策等）。只回答一个词：COURSE、STUDENT 或 POLICY。"
    prompt_en = "This question requires internal knowledge. Classify it into exactly ONE of: COURSE (course tasks, projects, exams), STUDENT (a specific student's submitted work or performance), POLICY (tuition, regulations, general academic policies). Answer with ONE WORD: COURSE, STUDENT or POLICY."
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
            if "STUDENT" in txt:
                return "STUDENT"
            if "POLICY" in txt:
                return "POLICY"
            if "COURSE" in txt:
                return "COURSE"
    except:
        pass
    q = query.lower()
    if re.search(r"\bcds\d{3}\b", q) or "assignment" in q or "project" in q or "exam" in q:
        return "COURSE"
    if "my assignment" in q or "my project" in q or "我提交" in q or "我的作业" in q:
        return "STUDENT"
    return "POLICY"


def _build_base_priorities(private_type: str, bases: List[str], target_course_bases: List[str], user_id: int | None) -> Tuple[Dict[str, float], List[str]]:
    priorities: Dict[str, float] = {}
    priority_bases: List[str] = []
    course_set = set(target_course_bases)
    for b in bases:
        p = 0.0
        if b == "public":
            kind = "public"
        elif b.startswith("course_"):
            kind = "course"
        elif b.startswith("user_") and b.endswith("_private"):
            kind = "user_private"
        else:
            kind = "other"
        if private_type == "COURSE":
            if b in course_set:
                p = max(p, 0.4)
            elif kind == "course":
                p = max(p, 0.2)
        elif private_type == "STUDENT":
            if user_id is not None and b == f"user_{user_id}_private":
                p = max(p, 0.5)
            elif kind == "user_private":
                p = max(p, 0.3)
            if b in course_set:
                p = max(p, 0.2)
        elif private_type == "POLICY":
            if kind == "public":
                p = max(p, 0.4)
            elif kind == "course":
                p = max(p, 0.1)
        if p > 0:
            priorities[b] = p
    if private_type == "COURSE":
        priority_bases = list(course_set) if course_set else [b for b in bases if b.startswith("course_")]
    elif private_type == "STUDENT":
        if user_id is not None:
            base_name = f"user_{user_id}_private"
            if base_name in bases:
                priority_bases.append(base_name)
        if not priority_bases:
            priority_bases = [b for b in bases if b.startswith("user_") and b.endswith("_private")]
        priority_bases.extend([b for b in bases if b in course_set])
    elif private_type == "POLICY":
        if "public" in bases:
            priority_bases = ["public"]
    seen = set()
    deduped = []
    for b in priority_bases:
        if b not in seen:
            seen.add(b)
            deduped.append(b)
    return priorities, deduped


def _effective_score(ref: Dict[str, Any], base_priorities: Dict[str, float]) -> float:
    score = _parse_similarity(ref.get("similarity", "0%"))
    base = ref.get("base")
    if base in base_priorities and score > 0:
        score *= 1.0 + base_priorities[base]
    return score


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

async def route_stream(current_question: str, previous_questions: List[str], language: str, bases: List[str], temp_file_content: str = None, user_id: int | None = None):
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

    print(f"DEBUG: Intent is PRIVATE. Starting retrieval.")
    private_type = await asyncio.to_thread(_classify_private_type_ollama, current_question, base_url, model, language)
    print(f"DEBUG: PRIVATE subtype is {private_type}.")

    try:
        search_query, assembled_question, generate_time = await generate_search_query(current_question, previous_questions)
    except:
        search_query = current_question
        assembled_question = current_question
        generate_time = 0.0

    references = []
    search_time = 0.0

    unique_bases = list(set(bases))
    print(f"DEBUG: Searching across bases: {unique_bases}")

    target_course_bases = _extract_course_bases_from_question(current_question)
    if target_course_bases:
        print(f"DEBUG: Detected course bases in question: {target_course_bases}")
    base_priorities, priority_bases = _build_base_priorities(private_type, unique_bases, target_course_bases, user_id)
    if base_priorities:
        print(f"DEBUG: Base priorities: {base_priorities}, priority_bases={priority_bases}")

    vector_only_count = 0
    tfidf_only_count = 0
    both_count = 0
    try:
        from backend.model.embedding import get_embedding
        from backend.model.vector_store import query_documents

        vector_start_time = time.time()
        # Get query embedding
        query_vec = get_embedding(search_query)

        if query_vec:
            for base in unique_bases:
                # Query ChromaDB
                results = query_documents(base, [query_vec], n_results=5)
                if results and results['documents']:
                    # Chroma returns list of lists
                    docs = results['documents'][0]
                    metas = results['metadatas'][0]
                    distances = results['distances'][0]

                    for i in range(len(docs)):
                        # Distance to similarity conversion (approximate)
                        # Chroma default is L2. Lower is better.
                        # We need to normalize to a score or percentage.
                        # Simple inversion: 1 / (1 + distance)
                        dist = distances[i]
                        # score = 1 / (1 + dist)
                        # With cosine distance: 0=identical, 1=orthogonal, 2=opposite.
                        score = max(0.0, 1.0 - dist)
                        sim_percent = f"{score * 100:.1f}%"

                        references.append({
                            "content": docs[i],
                            "base": base,
                            "file_name": metas[i].get("original_file", metas[i].get("source", "unknown")),
                            "similarity": sim_percent,
                            "retrieval_mode": "vector"
                        })
            search_time += (time.time() - vector_start_time)
            print(f"DEBUG: Vector search found {len(references)} results.")
        else:
            print("DEBUG: Failed to generate query embedding.")

    except Exception as e:
        print(f"Vector search error: {e}")

    # 2. 始终执行传统检索 (Always perform Traditional Search - Hybrid Mode)
    print("DEBUG: Performing traditional TF-IDF search for hybrid retrieval.")
    try:
        # 传统检索 (按顺序)
        for base in unique_bases:
            # 确保 piece_dir 正确指向存储切片的目录
            input_folder = piece_dir(base=base)
            if os.path.exists(input_folder):
                refs, t = await search_documents(search_query, load_segments_from_folder(input_folder=input_folder))
                for ref in refs:
                    if "base" not in ref:
                        ref["base"] = base
                    if "file_name" not in ref and "source" in ref:
                        ref["file_name"] = ref["source"]
                    if "retrieval_mode" not in ref:
                        ref["retrieval_mode"] = "tfidf"
                references.extend(refs)
                search_time += t
            else:
                print(f"DEBUG: Base directory not found: {input_folder}")
    except Exception as e:
        print(f"Search error: {e}")
        # references = [] # Do not clear, keep whatever we have
        search_time = 0.0

    # 对合并后的 references 按相似度降序排序
    # 注意：此时 references 可能包含重复内容（既被向量搜到，又被 TF-IDF 搜到）
    # 我们需要去重。
    unique_refs = {}
    for ref in references:
        key = ref.get("content", "")[:50]
        mode = ref.get("retrieval_mode", "")
        if key not in unique_refs:
            unique_refs[key] = ref
        else:
            existing = unique_refs[key]
            current_score = _parse_similarity(existing.get("similarity", "0%"))
            new_score = _parse_similarity(ref.get("similarity", "0%"))
            merged_mode = _merge_mode(existing.get("retrieval_mode", ""), mode)
            if new_score > current_score:
                ref["retrieval_mode"] = merged_mode
                unique_refs[key] = ref
            else:
                existing["retrieval_mode"] = merged_mode

    references = list(unique_refs.values())

    for ref in references:
        mode = ref.get("retrieval_mode", "")
        if mode == "vector":
            vector_only_count += 1
        elif mode == "tfidf":
            tfidf_only_count += 1
        elif mode == "both":
            both_count += 1

    references_sorted = sorted(references, key=lambda x: _effective_score(x, base_priorities), reverse=True)
    top_k = 5
    top = references_sorted[:top_k]
    if priority_bases:
        has_priority = any(ref.get("base") in priority_bases for ref in top)
        if not has_priority:
            candidate = next((ref for ref in references_sorted if ref.get("base") in priority_bases), None)
            if candidate:
                replace_idx = None
                for i in range(len(top) - 1, -1, -1):
                    if top[i].get("base") not in priority_bases:
                        replace_idx = i
                        break
                if replace_idx is not None:
                    top[replace_idx] = candidate
    references = top

    # Add temp file content if present
    if temp_file_content:
        references.insert(0, {
            "content": temp_file_content,
            "base": "temp",
            "file_name": "Uploaded Assignment/Document",
            "similarity": "100%"
        })

    threshold = float(os.getenv("SIMILARITY_THRESHOLD", "0.005"))
    max_score = 0.0
    for ref in references:
        if "similarity" in ref:
            max_score = max(max_score, _parse_similarity(ref["similarity"]))

    print(f"DEBUG: Max score: {max_score}, Threshold: {threshold}, References count: {len(references)}, "
          f"vector_only={vector_only_count}, tfidf_only={tfidf_only_count}, both={both_count}")

    # 3. 如果有高分结果，或者 intent 是 PRIVATE (即使用户认为它是private，但没搜到，我们也可以尝试用 RAG 风格回答，或者告诉用户没找到)
    # 这里的逻辑是：如果搜到了，就用 RAG。
    if max_score >= threshold and len(references) > 0:
        print("DEBUG: Entering RAG mode")
        gen = stream_answer(
            assembled_question,
            generate_time,
            references,
            search_time,
            target_language=language,
            private_type=private_type,
        )
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
