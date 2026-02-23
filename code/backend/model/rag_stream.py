import os
import json
import requests
from typing import Literal
import asyncio

async def stream_ollama_query(prompt: str):
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_GEN_MODEL", "qwen3:8b")

    try:
        # Note: requests.post is blocking. In a high-concurrency production env, use aiohttp.
        # For this local setup, it's acceptable, but we add asyncio.sleep(0) to yield control during iteration.
        with requests.post(
            f"{base_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": True},
            stream=True,
            timeout=300
        ) as r:
            if r.status_code != 200:
                yield f"Error: Ollama returned status {r.status_code}"
                return

            for line in r.iter_lines():
                if not line:
                    continue
                try:
                    obj = json.loads(line.decode("utf-8"))
                    chunk = obj.get("response")
                    if chunk:
                        yield chunk
                    if obj.get("done"):
                        break
                except:
                    pass
                # Yield control to event loop
                await asyncio.sleep(0)
    except Exception as e:
        yield f"Error connecting to Ollama: {str(e)}"

async def stream_answer(assembled_question: str, generate_time: float, references: list[dict[str, str]],
                        search_time: float, target_language: Literal['en', 'zh-cn', 'zh-tw'] = 'en',
                        private_type: str = "POLICY"):
    # Measure doc analysis time
    split_time = 0.0
    # Measure query generation time
    # Measure document search time
    # Measure LLM response time
    llm_time = 0.0

    # Print timing results
    print(f"1. Document Splitting Time: {split_time:.2f}s")
    print(f"2. Query Generation Time: {generate_time:.2f}s")
    print(f"3. Document Search Time: {search_time:.2f}s")
    print(f"4. LLM Response Generation Time: {llm_time:.2f}s")

    prompt = build_prompt(target_language, assembled_question, references, private_type)

    # 流式调用LLM (Switch to Ollama)
    async for chunk in stream_ollama_query(prompt):
        yield chunk


def build_prompt(language: Literal['en', 'zh-cn', 'zh-tw'], assembled_question, references, private_type: str) -> str:
    pt = (private_type or "").upper()
    context_str = "\n\n".join([f"[{i + 1}] {ref['content']}" for i, ref in enumerate(references)])
    if pt == "COURSE":
        if language == "zh-cn":
            return f"""你现在的角色是岭南大学课程与作业助手。
请根据下方【参考资料】中的课程资料和作业说明，用自己的话概括和回答用户的问题，可以做合理的归纳总结，不要求原文有一模一样的句子。
如果资料只涵盖部分信息，请先说明你能确定的部分，再说明哪些内容资料中没有明确写出。

【参考资料】：
{context_str}

【用户问题】：
{assembled_question}

【你的回答】："""
        if language == "zh-tw":
            return f"""你現在的角色是嶺南大學課程與作業助手。
請根據下方【參考資料】中的課程資料與作業說明，用自己的話概括並回答用戶的問題，可以做合理的歸納總結，不要求原文有一模一樣的句子。
如果資料只涵蓋部分資訊，請先說明你能確定的部分，再說明哪些內容資料中沒有明確寫出。

【參考資料】：
{context_str}

【用戶問題】：
{assembled_question}

【你的回答】："""
        return f"""You are a course and assignment assistant for Lingnan University.
Use the [References] about course outlines, lectures and assignment descriptions to answer the question.
You may summarize and infer the intent and requirements even if there is no explicit one-sentence definition in the text.
If the references only contain partial information, clearly state what can be inferred and which details are not explicitly specified.

[References]:
{context_str}

[User Question]:
{assembled_question}

[Answer]:"""
    if pt == "STUDENT":
        if language == "zh-cn":
            return f"""你现在的角色是老师，正在阅读学生的作业和课程要求。
请基于【参考资料】中的学生作业内容和课程/作业说明，给出具体的分析和建议，可以进行合理的归纳总结。
如果资料没有覆盖某些方面，请直接说明“资料中没有明确说明这一点”，不要凭空编造。

【参考资料】：
{context_str}

【用户问题】：
{assembled_question}

【你的回答】："""
        if language == "zh-tw":
            return f"""你現在的角色是老師，正在閱讀學生的作業與課程要求。
請根據【參考資料】中的學生作業內容與課程/作業說明，給出具體的分析與建議，可以進行合理的歸納總結。
如果資料沒有涵蓋某些面向，請直接說明「資料中沒有明確說明這一點」，不要憑空編造。

【參考資料】：
{context_str}

【用戶問題】：
{assembled_question}

【你的回答】："""
        return f"""You are a course instructor reviewing a student's work and the corresponding course requirements.
Use the [References] that include student submissions and assignment descriptions to analyze the question and provide concrete feedback.
You may summarize and draw reasonable conclusions from the text, but do not invent rules or requirements that are not supported by the documents.

[References]:
{context_str}

[User Question]:
{assembled_question}

[Answer]:"""
    return promt_select(language, assembled_question, references)


def promt_select(language: Literal['en', 'zh-cn', 'zh-tw'], assembled_question, references) -> str:
    context_str = "\n\n".join([f"[{i + 1}] {ref['content']}" for i, ref in enumerate(references)])

    if language == "zh-cn":
        return f"""你现在的角色是岭南大学政策问答助手。
请务必根据下方的【参考资料】来回答用户的问题。
如果在参考资料中找到了答案，请在回答中相应位置标注引用来源，格式为 [1], [2]。
如果参考资料中没有相关信息，请明确告知用户未找到相关政策，不要编造答案。

【参考资料】：
{context_str}

【用户问题】：
{assembled_question}

【你的回答】："""
    elif language == "zh-tw":
        return f"""你現在的角色是嶺南大學政策問答助手。
請務必根據下方的【參考資料】來回答用戶的問題。
如果在參考資料中找到了答案，請在回答中相應位置標註引用來源，格式為 [1], [2]。
如果參考資料中沒有相關資訊，請明確告知用戶未找到相關政策，不要編造答案。

【參考資料】：
{context_str}

【用戶問題】：
{assembled_question}

【你的回答】："""

    # English default
    return f"""You are a helpful assistant for Lingnan University.
Please answer the user's question STRICTLY based on the provided [References] below.
- If the information is in the references, answer the question and cite the source number like [1], [2] at the end of the sentence.
- If the references do not contain the answer, say "I cannot find the answer in the provided policy documents."
- Do not use your general knowledge to answer if it's not in the documents.

[References]:
{context_str}

[User Question]:
{assembled_question}

[Answer]:"""


if __name__ == "__main__":
    print("开始流式调用测试:\n")

    assembled_question_test = "History Questions: null;Current Questions: Can I use student card after graduated?"
    generate_time_test = 2.2
    references_test = [{'content': 'The Card will also be invalid once a student has terminated his/her studies.',
                        'source': 'TPg_Student_Handbook_2024-25_segmented.txt', 'similarity': '80.2%'}]
    search_time_test = 1.1
    language_test = "zh-tw"


    async def main():
        async for token in stream_answer(assembled_question_test, generate_time_test, references_test, search_time_test,
                                         language_test, "POLICY"):
            print(token, end='', flush=True)
        print("\n\n流式调用测试完成")


    asyncio.run(main())
