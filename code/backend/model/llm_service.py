import os
import requests
import json
import logging

# Vertex AI SDK
try:
    import vertexai
    from vertexai.generative_models import GenerativeModel
    HAS_VERTEX_AI = True
except ImportError:
    HAS_VERTEX_AI = False

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.disabled_providers = set()

        # Google Vertex AI (Service Account)
        self.vertex_project_id = os.getenv("VERTEX_PROJECT_ID")
        self.vertex_location = os.getenv("VERTEX_LOCATION", "us-central1")
        self.has_vertex_creds = bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS")) or bool(self.vertex_project_id)

        if self.has_vertex_creds and HAS_VERTEX_AI:
            try:
                vertexai.init(project=self.vertex_project_id, location=self.vertex_location)
                logger.info("Google Vertex AI configured successfully.")
            except Exception as e:
                logger.error(f"Failed to configure Google Vertex AI: {e}")
                self.has_vertex_creds = False
        elif self.has_vertex_creds and not HAS_VERTEX_AI:
            logger.warning("Vertex credentials found but google-cloud-aiplatform package is not installed.")
        elif not self.has_vertex_creds:
            logger.warning("No Vertex AI credentials found. Only Ollama will be available.")

    def get_embedding(self, text: str, model: str = "text-embedding-004", provider: str = "auto") -> list[float]:
        """
        Get embedding for the given text.
        Priority: Vertex AI -> Ollama (fallback)
        """
        # 1. Try Vertex AI
        if (provider == "vertex" or provider == "auto") and "vertex" not in self.disabled_providers:
            if self.has_vertex_creds and HAS_VERTEX_AI:
                try:
                    from vertexai.language_models import TextEmbeddingModel

                    vertex_model = TextEmbeddingModel.from_pretrained(model)
                    embeddings = vertex_model.get_embeddings([text])
                    if embeddings:
                        return embeddings[0].values
                except Exception as e:
                    logger.warning(f"Vertex AI embedding failed: {e}")
                    if "Unable to authenticate" in str(e) or "PermissionDenied" in str(e):
                        logger.error("Disabling Vertex AI provider due to authentication error.")
                        self.disabled_providers.add("vertex")

        # 2. Fallback to Ollama
        local_model = "nomic-embed-text"
        try:
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            api_url = f"{base_url.rstrip('/')}/api/embeddings"
            resp = requests.post(api_url, json={
                "model": local_model,
                "prompt": text
            }, timeout=30)
            if resp.status_code == 200:
                return resp.json().get("embedding")
        except Exception as e:
            logger.error(f"Ollama embedding fallback failed: {e}")

        return None

    def call_llm(self, prompt: str, task_type: str = "fast", system_instruction: str = None, fallback_model: str = "qwen:14b", fallback_base_url: str = "http://localhost:11434", provider: str = "auto") -> str:
        """
        Main entry point for LLM calls.
        Priority: Vertex AI -> Ollama (fallback).

        Args:
            prompt: The user prompt.
            task_type: "fast" (for routing/classification) or "complex" (for reasoning/generation).
            system_instruction: Optional system instruction.
            fallback_model: The local Ollama model to use as fallback.
            fallback_base_url: The local Ollama base URL.
            provider: "auto" (Vertex -> Ollama), "vertex" (force Vertex), "ollama" (force local).

        Returns:
            The generated text response.
        """
        model_name = "gemini-2.0-flash-001" if task_type == "fast" else "gemini-2.5-pro"

        if provider == "ollama":
            logger.info(f"Explicitly calling local Ollama ({fallback_model})...")
            return self._call_ollama(fallback_model, fallback_base_url, prompt, system_instruction)

        # provider == "vertex" or "auto" -> Try Vertex AI first
        if self.has_vertex_creds and HAS_VERTEX_AI:
            try:
                logger.info(f"Calling Google Vertex AI ({model_name})...")
                return self._call_vertex(model_name, prompt, system_instruction)
            except Exception as e:
                logger.warning(f"Google Vertex AI call failed: {e}. Falling back to Ollama...")

        # Fallback to Local Ollama
        logger.info(f"Calling local Ollama ({fallback_model})...")
        return self._call_ollama(fallback_model, fallback_base_url, prompt, system_instruction)

    def call_llm_stream(self, prompt: str, task_type: str = "fast", system_instruction: str = None, fallback_model: str = "qwen:14b", fallback_base_url: str = "http://localhost:11434", provider: str = "auto"):
        """
        Stream response from LLM.
        Priority: Vertex AI -> Ollama (fallback).
        """
        model_name = "gemini-2.0-flash-001" if task_type == "fast" else "gemini-2.5-pro"

        if provider == "ollama":
            logger.info(f"Explicitly streaming from local Ollama ({fallback_model})...")
            for chunk in self._call_ollama_stream(fallback_model, fallback_base_url, prompt, system_instruction):
                yield chunk
            return

        # provider == "vertex" or "auto" -> Try Vertex AI first
        if self.has_vertex_creds and HAS_VERTEX_AI:
            try:
                logger.info(f"Streaming from Google Vertex AI ({model_name})...")
                for chunk in self._call_vertex_stream(model_name, prompt, system_instruction):
                    yield chunk
                return
            except Exception as e:
                logger.warning(f"Google Vertex AI stream failed: {e}. Falling back to Ollama...")

        # Fallback to Local Ollama
        logger.info(f"Streaming from local Ollama ({fallback_model})...")
        for chunk in self._call_ollama_stream(fallback_model, fallback_base_url, prompt, system_instruction):
            yield chunk

    def _call_vertex(self, model_name: str, prompt: str, system_instruction: str = None) -> str:
        """Helper to call Google Vertex AI."""
        generation_config = {
            "temperature": 0.1 if "flash" in model_name else 0.7,
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 8192,
        }

        model = GenerativeModel(
            model_name=model_name,
            system_instruction=[system_instruction] if system_instruction else None
        )

        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )
        return response.text

    def _call_vertex_stream(self, model_name: str, prompt: str, system_instruction: str = None):
        """Helper to stream from Google Vertex AI."""
        generation_config = {
            "temperature": 0.1 if "flash" in model_name else 0.7,
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 8192,
        }

        model = GenerativeModel(
            model_name=model_name,
            system_instruction=[system_instruction] if system_instruction else None
        )

        response = model.generate_content(
            prompt,
            generation_config=generation_config,
            stream=True
        )
        for chunk in response:
            if chunk.text:
                yield chunk.text

    def _call_ollama(self, model: str, base_url: str, prompt: str, system_instruction: str = None) -> str:
        """Helper to call local Ollama API."""
        full_prompt = prompt
        if system_instruction:
            full_prompt = f"System: {system_instruction}\n\nUser: {prompt}"

        data = {
            "model": model,
            "prompt": full_prompt,
            "stream": False
        }

        try:
            # Ensure base_url doesn't end with slash if we append /api/generate
            api_url = f"{base_url.rstrip('/')}/api/generate"
            r = requests.post(api_url, json=data, timeout=30)

            if r.status_code == 200:
                try:
                    obj = r.json()
                    return obj.get("response", "").strip()
                except:
                    return r.text.strip()
            else:
                raise Exception(f"Ollama returned status code {r.status_code}")
        except Exception as e:
            logger.error(f"Ollama call failed: {e}")
            # If everything fails, return empty string or raise
            raise e

    def _call_ollama_stream(self, model: str, base_url: str, prompt: str, system_instruction: str = None):
        """Helper to stream from local Ollama API."""
        full_prompt = prompt
        if system_instruction:
            full_prompt = f"System: {system_instruction}\n\nUser: {prompt}"

        data = {
            "model": model,
            "prompt": full_prompt,
            "stream": True
        }

        try:
            api_url = f"{base_url.rstrip('/')}/api/generate"
            with requests.post(api_url, json=data, stream=True, timeout=300) as r:
                if r.status_code != 200:
                    raise Exception(f"Ollama returned status code {r.status_code}")

                for line in r.iter_lines():
                    if line:
                        try:
                            obj = json.loads(line.decode("utf-8"))
                            chunk = obj.get("response")
                            if chunk:
                                yield chunk
                        except:
                            pass
        except Exception as e:
            logger.error(f"Ollama stream failed: {e}")
            raise e

# Singleton instance
llm_service = LLMService()
