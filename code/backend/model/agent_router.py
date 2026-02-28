import os
import json
import time
import requests
import asyncio
import re
from typing import List, Dict, Tuple, Any, Optional
from backend.model.doc_search import search_documents, load_segments_from_folder
from backend.root_path import piece_dir
from backend.model.rag_stream import stream_answer
from backend.model.llm_service import llm_service


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


def _format_conversation_context(conversation_history: Optional[List[Dict]]) -> str:
    """Format conversation history into a readable string for LLM prompts."""
    if not conversation_history:
        return ""
    lines = []
    for turn in conversation_history[-3:]:
        lines.append(f"User: {turn['question']}")
        if turn.get('answer'):
            lines.append(f"Assistant: {turn['answer'][:500]}")
    return "\n".join(lines)


async def _rewrite_query(current_question: str, conversation_history: Optional[List[Dict]],
                         base_url: str, model: str) -> str:
    """
    Context-Aware Query Rewriting Agent.
    Takes the current question + conversation history and produces
    a self-contained search query that resolves all pronouns and references.
    """
    if not conversation_history:
        return current_question

    context_str = _format_conversation_context(conversation_history)

    prompt = f"""You are a query rewriting agent for a university RAG system.
Given the conversation history and the user's latest question, rewrite the latest question into a STANDALONE search query.

Rules:
- The rewritten query must be understandable WITHOUT any conversation history.
- Replace ALL pronouns (this, that, it, these) and vague references with their actual subjects from the history.
- Keep the rewritten query concise (1-2 sentences max).
- Preserve the user's original language (Chinese or English).
- If the latest question is already self-contained, return it as-is.

Conversation History:
{context_str}

Latest Question: {current_question}

Rewritten Query (output ONLY the rewritten query, nothing else):"""

    try:
        result = await asyncio.to_thread(
            llm_service.call_llm,
            prompt=prompt,
            task_type="fast",
            fallback_model=model,
            fallback_base_url=base_url,
            provider="vertex"
        )
        result = result.strip().strip('"').strip("'")
        if result and len(result) > 3:
            print(f"DEBUG: Query rewritten: '{current_question}' -> '{result}'")
            return result
    except Exception as e:
        print(f"Query rewrite error: {e}")

    return current_question


def _rrf_fusion(vector_refs: List[Dict], tfidf_refs: List[Dict], k: int = 60) -> List[Dict]:
    """
    Reciprocal Rank Fusion (RRF) to merge results from vector and TF-IDF retrievers.
    RRF(d) = sum( 1 / (k + rank) ) across all retrievers.
    This avoids the problem of incompatible score scales between retrievers.
    """
    doc_scores: Dict[str, Dict] = {}

    for rank, ref in enumerate(vector_refs):
        key = ref.get("content", "")[:120]
        doc_scores[key] = {
            "ref": {**ref, "retrieval_mode": "vector"},
            "rrf_score": 1.0 / (k + rank + 1)
        }

    for rank, ref in enumerate(tfidf_refs):
        key = ref.get("content", "")[:120]
        if key in doc_scores:
            doc_scores[key]["rrf_score"] += 1.0 / (k + rank + 1)
            doc_scores[key]["ref"]["retrieval_mode"] = "both"
        else:
            doc_scores[key] = {
                "ref": {**ref, "retrieval_mode": "tfidf"},
                "rrf_score": 1.0 / (k + rank + 1)
            }

    sorted_docs = sorted(doc_scores.values(), key=lambda x: x["rrf_score"], reverse=True)

    # Normalize RRF scores for display as similarity percentage
    if sorted_docs:
        max_rrf = sorted_docs[0]["rrf_score"]
        for item in sorted_docs:
            normalized = (item["rrf_score"] / max_rrf) * 100 if max_rrf > 0 else 0
            item["ref"]["similarity"] = f"{normalized:.1f}%"

    return [item["ref"] for item in sorted_docs]


def _build_assembled_question(current_question: str, conversation_history: Optional[List[Dict]]) -> str:
    """Build the full context string for the final generation prompt."""
    if not conversation_history:
        return current_question

    parts = []
    for turn in conversation_history[-3:]:
        parts.append(f"User: {turn['question']}")
        if turn.get('answer'):
            parts.append(f"Assistant: {turn['answer'][:500]}")
    parts.append(f"User: {current_question}")
    return "\n".join(parts)


async def _llm_stream(prompt: str, base_url: str, model: str, provider: str = "auto"):
    """Stream response from LLM (Vertex AI -> Ollama fallback)."""
    try:
        for chunk in llm_service.call_llm_stream(prompt, task_type="fast", fallback_model=model, fallback_base_url=base_url, provider=provider):
            yield chunk
            await asyncio.sleep(0)
    except Exception as e:
        print(f"Stream error: {e}")
        return


async def _stream_text(text: str, chunk_size: int = 120):
    if not text:
        return
    for i in range(0, len(text), chunk_size):
        yield text[i:i + chunk_size]
        await asyncio.sleep(0)


def _clean_json_text(text: str) -> str:
    if not text:
        return ""
    t = text.strip()
    if t.startswith("```json"):
        t = t[7:]
    if t.startswith("```"):
        t = t[3:]
    if t.endswith("```"):
        t = t[:-3]
    t = t.strip()
    start = t.find("{")
    end = t.rfind("}")
    if start >= 0 and end > start:
        return t[start:end + 1]
    # Try finding list
    start_list = t.find("[")
    end_list = t.rfind("]")
    if start_list >= 0 and end_list > start_list:
        return t[start_list:end_list + 1]
    return t


def _summarize_references_for_gate(references: List[Dict[str, Any]], max_refs: int = 5, max_chars: int = 260) -> str:
    lines = []
    for i, r in enumerate((references or [])[:max_refs]):
        file_name = r.get("file_name") or r.get("source") or "unknown"
        base = r.get("base") or "unknown"
        sim = r.get("similarity") or "unknown"
        content = (r.get("content") or "").replace("\n", " ").strip()
        if len(content) > max_chars:
            content = content[:max_chars] + "..."
        lines.append(f"[{i+1}] base={base} file={file_name} sim={sim} text={content}")
    return "\n".join(lines)


def _expand_query_heuristic(query: str, language: str) -> str:
    q = (query or "").strip()
    if not q:
        return q
    if language.lower().startswith("zh"):
        extra = " 提交 要求 截止时间 ddl 评分标准 rubric 格式 format 交付 deliverables 作业说明 instructions"
    else:
        extra = " submission requirements due date deadline ddl grading rubric format deliverables instructions"
    return f"{q}{extra}"


async def _retrieval_quality_gate(current_question: str, rewritten_query: str, references: List[Dict[str, Any]],
                                  language: str, base_url: str, model: str) -> Dict[str, Any]:
    refs_summary = _summarize_references_for_gate(references)
    if language.lower().startswith("zh"):
        prompt = f"""你是一个 RAG 检索质量 Gate（只做评估，不要回答问题）。
请根据“用户问题 + 改写后的检索 query + 检索到的参考资料摘要”判断：当前资料是否足以严谨回答用户问法。

你必须输出严格合法 JSON（不要 Markdown），字段如下：
{{
  "answerable": true/false,
  "action": "generate" | "reretrieve" | "ask_clarify",
  "failure_type": "off_topic" | "missing_evidence" | "ambiguous_query" | "retrieval_bias" | "other",
  "reason": "一句话原因",
  "suggested_query": "如果需要重检索，给出更好的检索 query；否则留空字符串",
  "clarifying_question": "如果需要用户澄清，给出一个中文追问；否则留空字符串"
}}

用户问题：
{current_question}

改写后的检索 query：
{rewritten_query}

参考资料摘要（Top {min(len(references or []), 5)}）：
{refs_summary}

JSON："""
    else:
        prompt = f"""You are a RAG retrieval quality gate (evaluate only; do NOT answer the user).
Given: user question + rewritten retrieval query + summaries of retrieved references,
decide whether the references are sufficient to answer the question rigorously.

Output STRICT valid JSON only (no Markdown) with fields:
{{
  "answerable": true/false,
  "action": "generate" | "reretrieve" | "ask_clarify",
  "failure_type": "off_topic" | "missing_evidence" | "ambiguous_query" | "retrieval_bias" | "other",
  "reason": "one-sentence reason",
  "suggested_query": "if reretrieve, propose a better query; else empty string",
  "clarifying_question": "if ask_clarify, a question to ask user; else empty string"
}}

User question:
{current_question}

Rewritten retrieval query:
{rewritten_query}

Reference summaries (Top {min(len(references or []), 5)}):
{refs_summary}

JSON:"""

    try:
        response_text = await asyncio.to_thread(
            llm_service.call_llm,
            prompt=prompt,
            task_type="fast",
            fallback_model=model,
            fallback_base_url=base_url,
            provider="vertex"
        )
        cleaned = _clean_json_text(response_text)
        plan = json.loads(cleaned)
        if not isinstance(plan, dict):
            return {"answerable": True, "action": "generate", "failure_type": "other", "reason": "gate_non_dict", "suggested_query": "", "clarifying_question": ""}
        plan.setdefault("answerable", True)
        plan.setdefault("action", "generate")
        plan.setdefault("failure_type", "other")
        plan.setdefault("reason", "")
        plan.setdefault("suggested_query", "")
        plan.setdefault("clarifying_question", "")
        return plan
    except Exception as e:
        print(f"Gate error: {e}")
        return {"answerable": True, "action": "generate", "failure_type": "other", "reason": "gate_error", "suggested_query": "", "clarifying_question": ""}


async def _hybrid_retrieve(query: str, target_collections: List[str]) -> Tuple[List[Dict[str, Any]], float]:
    search_time = 0.0
    vector_refs: List[Dict[str, Any]] = []
    try:
        from backend.model.embedding import get_embedding
        from backend.model.vector_store import query_documents

        vector_start_time = time.time()
        query_vec = get_embedding(query)
        if query_vec:
            results = query_documents(target_collections, [query_vec], n_results=20)
            if results and results.get("documents"):
                docs = results["documents"][0]
                metas = results["metadatas"][0]
                distances = results["distances"][0]
                for i in range(len(docs)):
                    dist = distances[i]
                    score = max(0.0, 1.0 - dist)
                    sim_percent = f"{score * 100:.1f}%"
                    base_name = metas[i].get("collection_name", "unknown")
                    vector_refs.append({
                        "content": docs[i],
                        "base": base_name,
                        "file_name": metas[i].get("original_file", metas[i].get("source", "unknown")),
                        "similarity": sim_percent,
                    })
        search_time += (time.time() - vector_start_time)
    except Exception as e:
        print(f"Vector search error: {e}")

    tfidf_refs: List[Dict[str, Any]] = []
    try:
        for base_name in target_collections:
            input_folder = piece_dir(base=base_name)
            if os.path.exists(input_folder):
                refs, t = await search_documents(query, load_segments_from_folder(input_folder=input_folder))
                for ref in refs:
                    if "base" not in ref:
                        ref["base"] = base_name
                    if "file_name" not in ref and "source" in ref:
                        ref["file_name"] = ref["source"]
                tfidf_refs.extend(refs)
                search_time += t
    except Exception as e:
        print(f"TF-IDF Search error: {e}")

    references = _rrf_fusion(vector_refs, tfidf_refs)[:5]
    return references, search_time


async def _planner_agent(query: str, base_url: str, model: str, language: str,
                         conversation_history: Optional[List[Dict]] = None) -> Dict[str, Any]:
    """
    Unified Planner Agent: Determines Intent and Search Scope in one go.
    Returns JSON:
    {
        "intent": "rag_query" | "chat" | "web_search",
        "search_scope": ["public", "course_CDS524", ...],
        "reasoning": "...",
        "keywords": ["..."]
    }
    """
    # Build conversation context for Planner
    conv_context = ""
    if conversation_history:
        conv_context_lines = []
        for turn in conversation_history[-2:]:
            conv_context_lines.append(f"User: {turn['question']}")
            if turn.get('answer'):
                conv_context_lines.append(f"Assistant: {turn['answer'][:200]}")
        conv_context = "\n".join(conv_context_lines)

    conv_section_cn = f"对话历史 (供参考):\n{conv_context}" if conv_context else "对话历史: 无"
    conv_section_en = f"Conversation History (for reference):\n{conv_context}" if conv_context else "No conversation history."

    prompt_cn = f"""你是一个大学 RAG 系统的智能规划 Agent (Master Planner)。
请分析用户问题（结合对话历史），输出 JSON 格式的执行计划。

可用资源 (Collections):
- "public": 学校政策、奖学金、校园生活、行政通知等公共信息。
- "course_CODE": 特定课程资料 (例如 "course_CDS524", "course_CDS527")。
- "user_ID_private": 用户的私人上传文件。

输出规则:
1. intent:
   - "rag_query": 需要查询知识库 (包括课程、政策、作业等)。也包括用户追问上一轮 RAG 结果的情况。
   - "chat": 纯闲聊、打招呼、通用知识 (如"你好", "1+1等于几")。
2. search_scope: 如果是 rag_query，列出相关 collection names。
3. reasoning: 简短解释。

请仅输出合法的 JSON 字符串，不要包含 Markdown 格式。
{conv_section_cn}
"""
    prompt_en = f"""You are the Master Planner Agent for a University RAG system.
Analyze the user query (considering conversation history) and output a JSON execution plan.

Available Collections:
- "public": University policies, scholarships, campus life, admin notices.
- "course_CODE": Specific course materials (e.g., "course_CDS524").
- "user_ID_private": User's private files.

Rules:
1. intent:
   - "rag_query": Needs knowledge retrieval. This INCLUDES follow-up questions about previous RAG results.
   - "chat": Purely chitchat, greetings, general knowledge.
2. search_scope: If rag_query, list relevant collection names.
3. reasoning: Brief explanation.

Output ONLY valid JSON. No Markdown.
{conv_section_en}
"""
    prompt = prompt_cn if language.lower().startswith("zh") else prompt_en

    try:
        response_text = await asyncio.to_thread(
            llm_service.call_llm,
            prompt=f"{prompt}\nUser Query: {query}\nJSON Plan:",
            task_type="fast",
            fallback_model=model,
            fallback_base_url=base_url,
            provider="vertex"
        )

        # Clean up response to ensure valid JSON
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]

        plan = json.loads(response_text)
        return plan
    except Exception as e:
        print(f"Planner Agent Error: {e}")
        # Fallback plan
        return {
            "intent": "rag_query",
            "search_scope": ["public"],
            "reasoning": "Fallback due to error."
        }


async def route_stream(current_question: str, previous_questions: List[str], language: str, bases: List[str],
                       temp_file_content: str = None, user_id: int | None = None,
                       conversation_history: Optional[List[Dict]] = None):
    start_t = time.time()
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_GEN_MODEL", "qwen3:8b")

    # ====================================================================
    # STEP 1: Master Planner Agent (with conversation context)
    # ====================================================================
    print(f"DEBUG: Invoking Master Planner for query: '{current_question}'")
    plan = await _planner_agent(current_question, base_url, model, language, conversation_history)

    intent = plan.get("intent", "rag_query")
    search_scope = plan.get("search_scope", [])
    reasoning = plan.get("reasoning", "")

    print(f"DEBUG: Planner Result -> Intent: {intent}, Scope: {search_scope}, Reasoning: {reasoning}")

    # ====================================================================
    # STEP 2: Handle 'chat' Intent (with conversation context for continuity)
    # ====================================================================
    if intent == "chat":
        print(f"DEBUG: Intent is CHAT. Skipping retrieval.")
        conv_context = _format_conversation_context(conversation_history)
        if conv_context:
            prompt_prefix = f"Conversation History:\n{conv_context}\n\n"
        else:
            prompt_prefix = ""
        prompt_cn = "请直接回答用户的问题："
        prompt_en = "Answer the user's question directly:"
        prompt = prompt_cn if language.lower().startswith("zh") else prompt_en
        gen = _llm_stream(f"{prompt_prefix}{prompt}\n{current_question}", base_url, model, provider="vertex")
        # For chat, rewritten_query is same as current, scope is empty
        return gen, [], current_question, []

    # ====================================================================
    # STEP 3: Context-Aware Query Rewriting Agent
    # ====================================================================
    rewritten_query = await _rewrite_query(current_question, conversation_history, base_url, model)

    # ====================================================================
    # STEP 4: Determine search scope
    # ====================================================================
    target_collections = search_scope
    if not target_collections:
        target_collections = ["public"]
        regex_courses = _extract_course_bases_from_question(rewritten_query)
        if regex_courses:
            target_collections.extend(regex_courses)

    target_collections = list(set(target_collections))
    print(f"DEBUG: Final Search Scope: {target_collections}")

    # Build assembled question with full conversation context for the generation prompt
    assembled_question = _build_assembled_question(current_question, conversation_history)

    references, search_time = await _hybrid_retrieve(rewritten_query, target_collections)
    vector_only = sum(1 for r in references if r.get("retrieval_mode") == "vector")
    tfidf_only = sum(1 for r in references if r.get("retrieval_mode") == "tfidf")
    both_count = sum(1 for r in references if r.get("retrieval_mode") == "both")
    print(f"DEBUG: RRF Top 5 -> vector_only={vector_only}, tfidf_only={tfidf_only}, both={both_count}")

    # Add temp file content if present
    if temp_file_content:
        references.insert(0, {
            "content": temp_file_content,
            "base": "temp",
            "file_name": "Uploaded Document",
            "similarity": "100%"
        })

    # ====================================================================
    # STEP 8: Generate Response
    # ====================================================================
    has_content = len(references) > 0 and any(
        _parse_similarity(r.get("similarity", "0%")) > 0.005 for r in references
    )

    # Pass rewritten_query and scope back to caller
    # gen = stream_answer(assembled_question, 0.0, references, search_time, language, "POLICY")
    # return gen, references, rewritten_query, target_collections

    if has_content:
        gate = await _retrieval_quality_gate(current_question, rewritten_query, references, language, base_url, model)
        print(f"DEBUG: Gate -> answerable={gate.get('answerable')} action={gate.get('action')} type={gate.get('failure_type')} reason={gate.get('reason')}")

        if not gate.get("answerable", True) and gate.get("action") in ("reretrieve", "ask_clarify"):
            if gate.get("action") == "reretrieve":
                suggested_query = (gate.get("suggested_query") or "").strip()
                if not suggested_query:
                    suggested_query = _expand_query_heuristic(rewritten_query, language)
                print(f"DEBUG: Gate triggered reretrieve with query: {suggested_query}")
                references2, search_time2 = await _hybrid_retrieve(suggested_query, target_collections)
                if temp_file_content:
                    references2.insert(0, {
                        "content": temp_file_content,
                        "base": "temp",
                        "file_name": "Uploaded Document",
                        "similarity": "100%"
                    })
                has_content2 = len(references2) > 0 and any(
                    _parse_similarity(r.get("similarity", "0%")) > 0.005 for r in references2
                )
                if has_content2:
                    gate2 = await _retrieval_quality_gate(current_question, suggested_query, references2, language, base_url, model)
                    print(f"DEBUG: Gate2 -> answerable={gate2.get('answerable')} action={gate2.get('action')} type={gate2.get('failure_type')} reason={gate2.get('reason')}")
                    if gate2.get("answerable", False):
                        references = references2
                        search_time += search_time2
                        rewritten_query = suggested_query
                    else:
                        gate = gate2
                        references = references2
                        search_time += search_time2
                else:
                    gate = {"answerable": False, "action": "ask_clarify", "failure_type": "missing_evidence", "reason": "no_references_after_reretrieve", "suggested_query": suggested_query, "clarifying_question": ""}
                    references = references2
                    search_time += search_time2

            if not gate.get("answerable", True) and gate.get("action") == "ask_clarify":
                top_files = []
                for r in (references or [])[:3]:
                    fn = r.get("file_name") or r.get("source") or "unknown"
                    if fn not in top_files:
                        top_files.append(fn)
                files_str = "；".join(top_files) if language.lower().startswith("zh") else "; ".join(top_files)
                clarifying = (gate.get("clarifying_question") or "").strip()
                if not clarifying:
                    if language.lower().startswith("zh"):
                        clarifying = "你更想问的是：截止时间、提交方式/格式、评分标准，还是作业内容概述？请选一个并尽量包含课程号与作业编号。"
                    else:
                        clarifying = "Which part do you mean: due date, submission format/method, grading rubric, or assignment overview? Please include course code and assignment number."
                if language.lower().startswith("zh"):
                    msg = f"我检索到的资料暂时不足以严谨回答你当前的问法（原因：{gate.get('failure_type')} / {gate.get('reason')}）。\n当前命中的主要文件：{files_str}\n\n{clarifying}"
                else:
                    msg = f"The retrieved references are not sufficient to answer your question rigorously (reason: {gate.get('failure_type')} / {gate.get('reason')}).\nTop matched files: {files_str}\n\n{clarifying}"
                return _stream_text(msg), references, rewritten_query, target_collections

        print(f"DEBUG: Entering RAG generation mode with {len(references)} references")
        gen = stream_answer(
            assembled_question,
            0.0,
            references,
            search_time,
            target_language=language,
            private_type="RAG",
            provider="vertex"
        )
        return gen, references, rewritten_query, target_collections
    else:
        print(f"DEBUG: No relevant docs found. Fallback to direct answer.")
        conv_context = _format_conversation_context(conversation_history)
        context_prefix = f"Conversation History:\n{conv_context}\n\n" if conv_context else ""
        prompt_cn = "并未在知识库中找到相关文档，请尝试利用你的通用知识回答（请告知用户未找到校内信息）："
        prompt_en = "No relevant documents found in knowledge base. Please answer using general knowledge (warn user):"
        prompt = prompt_cn if language.lower().startswith("zh") else prompt_en
        gen = _llm_stream(f"{context_prefix}{prompt}\n{current_question}", base_url, model, provider="vertex")
        return gen, [], rewritten_query, target_collections


async def generate_follow_up_questions(current_question: str, answer: str, language: str) -> List[str]:
    """
    Generate 3 follow-up questions based on the current Q&A.
    """
    try:
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        model = os.getenv("OLLAMA_GEN_MODEL", "qwen3:8b")

        prompt_cn = f"""请根据用户问题和助手回答，生成3个用户可能感兴趣的后续问题。
用户问题: {current_question}
助手回答: {answer[:500]}...

请直接输出一个JSON字符串列表，例如：["问题1", "问题2", "问题3"]。不要包含Markdown格式。"""

        prompt_en = f"""Based on the user question and assistant answer, generate 3 likely follow-up questions.
User Question: {current_question}
Assistant Answer: {answer[:500]}...

Output ONLY a JSON list of strings, e.g., ["Question 1", "Question 2", "Question 3"]. No Markdown."""

        prompt = prompt_cn if language.lower().startswith("zh") else prompt_en

        response_text = await asyncio.to_thread(
            llm_service.call_llm,
            prompt=prompt,
            task_type="fast",
            fallback_model=model,
            fallback_base_url=base_url,
            provider="vertex"
        )

        cleaned = _clean_json_text(response_text)
        questions = json.loads(cleaned)
        if isinstance(questions, list):
            return questions[:3]
        return []
    except Exception as e:
        print(f"Follow-up generation error: {e}")
        return []
