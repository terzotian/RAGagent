from backend.model.llm_service import llm_service

def get_embedding(text: str, model: str = "text-embedding-004"):
    """
    Get embedding using LLMService (Vertex > Gemini > Ollama).
    """
    # Note: 'model' parameter is passed to LLMService, which defaults to 'text-embedding-004'
    # If the user passes a specific model (like 'bge-m3'), it might fail on Vertex/Gemini if not supported.
    # However, since we are enforcing Google ecosystem, we should probably ignore 'bge-m3' if passed
    # and default to 'text-embedding-004' unless explicitly overridden for local dev.

    # But for compatibility with existing calls that might pass 'nomic-embed-text',
    # we'll let LLMService handle the logic or we can override here.

    # Actually, LLMService.get_embedding has default 'text-embedding-004'.
    # If we pass 'bge-m3' to Vertex, it will likely fail.
    # So we should be careful.

    # If the caller requests a specific local model (like 'nomic-embed-text'),
    # we might want to respect it IF we are in local mode.
    # But the user said "Ollama only as fallback".

    # Let's trust LLMService to handle the priority.
    # We will pass 'model' but if it's a local model name, Vertex might error out?
    # Vertex.from_pretrained("nomic-embed-text") -> Error.

    # So we should probably default to "text-embedding-004" if the passed model is "nomic-embed-text" or "bge-m3"
    # UNLESS we explicitly want local.

    if model in ["nomic-embed-text", "bge-m3", "qwen:14b"]:
        # Upgrade to Vertex model if possible
        model = "text-embedding-004"

    return llm_service.get_embedding(text, model=model)
