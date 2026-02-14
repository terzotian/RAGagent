import requests
import os
import time

def get_embedding(text: str, model: str = "nomic-embed-text"):
    """
    Get embedding from Ollama.
    """
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    # Retry logic
    max_retries = 3
    for i in range(max_retries):
        try:
            resp = requests.post(f"{base_url}/api/embeddings", json={
                "model": model,
                "prompt": text
            }, timeout=30)
            if resp.status_code == 200:
                return resp.json().get("embedding")
            else:
                print(f"Error getting embedding (status {resp.status_code}): {resp.text}")
                if i < max_retries - 1:
                    time.sleep(1)
        except Exception as e:
            print(f"Error connecting to Ollama for embedding: {e}")
            if i < max_retries - 1:
                time.sleep(1)
    return None
