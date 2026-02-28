import os
import json
import requests
from typing import Literal
import asyncio

from backend.model.llm_service import llm_service

async def stream_answer(assembled_question: str, generate_time: float, references: list[dict[str, str]],
                        search_time: float, target_language: Literal['en', 'zh-cn', 'zh-tw'] = 'en',
                        private_type: str = "POLICY", provider: str = "vertex"):
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

    # Use LLM Service (Gemini Priority -> Ollama Fallback)
    # We use "complex" task type for RAG answers to use Gemini Pro if available
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_GEN_MODEL", "qwen3:8b")

    try:
        for chunk in llm_service.call_llm_stream(
            prompt=prompt,
            task_type="complex",
            fallback_model=model,
            fallback_base_url=base_url,
            provider=provider
        ):
            yield chunk
            await asyncio.sleep(0)
    except Exception as e:
        yield f"Error generating answer: {str(e)}"


def build_prompt(language: Literal['en', 'zh-cn', 'zh-tw'], assembled_question, references, private_type: str) -> str:
    pt = (private_type or "").upper()
    context_str = "\n\n".join([f"[{i + 1}] {ref['content']}" for i, ref in enumerate(references)])
    if pt == "COURSE":
        if language == "zh-cn":
            return f"""你现在的角色是岭南大学课程与作业助手。
请根据下方【参考资料】中的课程资料和作业说明回答用户问题。
请严格按照以下结构输出回答：

1. **核心结论**：直接回答用户问题的关键点。
2. **详细依据**：结合参考资料中的具体内容（如作业要求、课程大纲章节等）进行解释。
3. **补充说明/缺失信息**：如果资料不完整，说明哪些信息是推断的，或者哪些信息资料中未包含。

【参考资料】：
{context_str}

【用户问题】：
{assembled_question}

【你的回答】："""
        if language == "zh-tw":
            return f"""你現在的角色是嶺南大學課程與作業助手。
請根據下方【參考資料】中的課程資料與作業說明回答用戶問題。
請嚴格按照以下結構輸出回答：

1. **核心結論**：直接回答用戶問題的關鍵點。
2. **詳細依據**：結合參考資料中的具體內容（如作業要求、課程大綱章節等）進行解釋。
3. **補充說明/缺失資訊**：如果資料不完整，說明哪些資訊是推斷的，或者哪些資訊資料中未包含。

【參考資料】：
{context_str}

【用戶問題】：
{assembled_question}

【你的回答】："""
        return f"""You are a course and assignment assistant for Lingnan University.
Use the [References] about course outlines, lectures and assignment descriptions to answer the question.
Please structure your answer as follows:

1. **Core Conclusion**: Directly answer the key point of the user's question.
2. **Detailed Basis**: Explain using specific content from the references (e.g., assignment requirements, course sections).
3. **Note/Missing Info**: If information is incomplete, state what is inferred or missing from the documents.

[References]:
{context_str}

[User Question]:
{assembled_question}

[Answer]:"""
    if pt == "STUDENT":
        if language == "zh-cn":
            return f"""你现在的角色是老师，正在阅读学生的作业和课程要求。
请基于【参考资料】中的学生作业内容和课程/作业说明，给出具体的分析和建议。
请严格按照以下结构输出回答：

1. **核心结论**：直接回答用户问题的关键点。
2. **详细分析**：结合参考资料中的具体内容进行解释。
3. **建议/缺失信息**：如果资料不完整，说明哪些信息是推断的，或者哪些信息资料中未包含。

【参考资料】：
{context_str}

【用户问题】：
{assembled_question}

【你的回答】："""
        if language == "zh-tw":
            return f"""你現在的角色是老師，正在閱讀學生的作業與課程要求。
請基於【參考資料】中的學生作業內容與課程/作業說明，給出具體的分析與建議。
請嚴格按照以下結構輸出回答：

1. **核心結論**：直接回答用戶問題的關鍵點。
2. **詳細分析**：結合參考資料中的具體內容進行解釋。
3. **建議/缺失資訊**：如果資料不完整，說明哪些資訊是推斷的，或者哪些資訊資料中未包含。

【參考資料】：
{context_str}

【用戶問題】：
{assembled_question}

【你的回答】："""
        return f"""You are a course instructor reviewing a student's work and the corresponding course requirements.
Use the [References] that include student submissions and assignment descriptions to analyze the question and provide concrete feedback.
Please structure your answer as follows:

1. **Core Conclusion**: Directly answer the key point of the user's question.
2. **Detailed Analysis**: Explain using specific content from the references.
3. **Suggestion/Missing Info**: If information is incomplete, state what is inferred or missing from the documents.

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
请严格按照以下结构输出回答：

1. **核心结论**：直接回答用户问题的关键点。
2. **详细依据**：结合参考资料中的具体内容进行解释，并在相应位置标注引用来源，格式为 [1], [2]。
3. **补充说明/缺失信息**：如果资料不完整，说明哪些信息是推断的，或者哪些信息资料中未包含。

【参考资料】：
{context_str}

【用户问题】：
{assembled_question}

【你的回答】："""
    elif language == "zh-tw":
        return f"""你現在的角色是嶺南大學政策問答助手。
請務必根據下方的【參考資料】來回答用戶的問題。
請嚴格按照以下結構輸出回答：

1. **核心結論**：直接回答用戶問題的關鍵點。
2. **詳細依據**：結合參考資料中的具體內容進行解釋，並在相應位置標註引用來源，格式為 [1], [2]。
3. **補充說明/缺失資訊**：如果資料不完整，說明哪些資訊是推斷的，或者哪些資訊資料中未包含。

【參考資料】：
{context_str}

【用戶問題】：
{assembled_question}

【你的回答】："""

    # English default
    return f"""You are a helpful assistant for Lingnan University.
Please answer the user's question STRICTLY based on the provided [References] below.
Please structure your answer as follows:

1. **Core Conclusion**: Directly answer the key point of the user's question.
2. **Detailed Basis**: Explain using specific content from the references, citing source numbers like [1], [2] at the end of sentences.
3. **Note/Missing Info**: If information is incomplete, state what is inferred or missing from the documents.

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
