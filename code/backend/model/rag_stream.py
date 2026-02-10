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
                        search_time: float, target_language: Literal['en', 'zh-cn', 'zh-tw'] = 'en'):
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

    prompt = promt_select(target_language, assembled_question, references)

    # 流式调用LLM (Switch to Ollama)
    async for chunk in stream_ollama_query(prompt):
        yield chunk


def promt_select(language: Literal['en', 'zh-cn', 'zh-tw'], assembled_question, references) -> str:
    # Build context string
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
                                         language_test):
            print(token, end='', flush=True)
        print("\n\n流式调用测试完成")


    asyncio.run(main())
