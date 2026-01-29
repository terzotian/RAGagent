
import os
import asyncio
from dotenv import load_dotenv

# 手动加载 .env，确保路径正确
load_dotenv(".env")

from backend.model.llm_stream_tongyiqianwen import stream_qwen_plus_query

async def main():
    print(f"API Key from env: {os.getenv('tongyiqianwen')}")
    try:
        print("Start testing LLM...")
        async for token in stream_qwen_plus_query("你好，测试一下连接"):
            print(token, end='', flush=True)
        print("\nTest finished.")
    except Exception as e:
        print(f"\nError occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
