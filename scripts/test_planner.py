
import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path="code/backend/.env")

# Add project root to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(root_dir, "code"))

from backend.model.agent_router import _planner_agent, _extract_course_bases_from_question

async def test_planner():
    print("--- Testing Master Planner Agent ---")

    test_cases = [
        ("你好", "zh"),
        ("How to apply for scholarship?", "en"),
        ("CDS524的作业什么时候交？", "zh"),
        ("Tell me about CDS524 and CDS527", "en"),
        ("我想知道关于深度学习的课程", "zh"), # Ambiguous
        ("How to graduate?", "en")
    ]

    # Mock LLM Service env vars if needed, but assuming .env is loaded or env is set
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_GEN_MODEL", "qwen3:8b")

    for query, lang in test_cases:
        print(f"\nQuery: {query} [{lang}]")
        try:
            plan = await _planner_agent(query, base_url, model, lang)
            print(f"Plan: {plan}")

            # Basic Validation
            intent = plan.get("intent")
            scope = plan.get("search_scope", [])

            if "CDS524" in query and "course_CDS524" not in scope:
                print("❌ FAIL: Expected course_CDS524 in scope")
            elif "scholarship" in query.lower() and "public" not in scope:
                print("❌ FAIL: Expected public in scope")
            elif query == "你好" and intent != "chat":
                print("❌ FAIL: Expected chat intent")
            else:
                print("✅ PASS")

        except Exception as e:
            print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_planner())
