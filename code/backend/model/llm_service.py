import os
import requests
import json
import logging

# Try to import Google Generative AI library
try:
    import google.generativeai as genai
    HAS_GOOGLE_GENAI = True
except ImportError:
    HAS_GOOGLE_GENAI = False

# Try to import Vertex AI library
try:
    import vertexai
    from vertexai.generative_models import GenerativeModel
    HAS_VERTEX_AI = True
except ImportError:
    HAS_VERTEX_AI = False

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        # 1. Google AI Studio (API Key)
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.has_google_key = bool(self.google_api_key)

        if self.has_google_key and HAS_GOOGLE_GENAI:
            try:
                genai.configure(api_key=self.google_api_key)
                logger.info("Google Generative AI configured successfully.")
            except Exception as e:
                logger.error(f"Failed to configure Google Generative AI: {e}")
                self.has_google_key = False
        elif self.has_google_key and not HAS_GOOGLE_GENAI:
            logger.warning("GOOGLE_API_KEY found but google-generativeai package is not installed.")

        # 2. Google Vertex AI (Service Account)
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

    def call_llm(self, prompt: str, task_type: str = "fast", system_instruction: str = None, fallback_model: str = "qwen:14b", fallback_base_url: str = "http://localhost:11434", provider: str = "auto") -> str:
        """
        Main entry point for LLM calls.
        Prioritizes Google Gemini API (AI Studio) -> Vertex AI -> Local Ollama.

        Args:
            prompt: The user prompt.
            task_type: "fast" (for routing/classification) or "complex" (for reasoning/generation).
            system_instruction: Optional system instruction (supported by Gemini).
            fallback_model: The local model to use if Gemini fails (e.g., "qwen:14b").
            fallback_base_url: The local Ollama base URL.
            provider: "auto" (default priority), "gemini" (force AI Studio), "vertex" (force Vertex AI), "ollama" (force Local).

        Returns:
            The generated text response.
        """
        model_name = "gemini-1.5-flash" if task_type == "fast" else "gemini-1.5-pro"

        # Explicit Provider Selection
        if provider == "gemini":
            if self.has_google_key and HAS_GOOGLE_GENAI:
                try:
                    logger.info(f"Explicitly calling Google Gemini AI Studio ({model_name})...")
                    return self._call_gemini(model_name, prompt, system_instruction)
                except Exception as e:
                    logger.warning(f"Explicit Google Gemini AI Studio call failed: {e}. Falling back to Ollama...")
            else:
                 logger.warning("Provider 'gemini' requested but not configured. Falling back to Ollama...")
            return self._call_ollama(fallback_model, fallback_base_url, prompt, system_instruction)

        if provider == "vertex":
            if self.has_vertex_creds and HAS_VERTEX_AI:
                try:
                    logger.info(f"Explicitly calling Google Vertex AI ({model_name})...")
                    return self._call_vertex(model_name, prompt, system_instruction)
                except Exception as e:
                    logger.warning(f"Explicit Google Vertex AI call failed: {e}. Falling back to Ollama...")
            else:
                 logger.warning("Provider 'vertex' requested but not configured. Falling back to Ollama...")
            return self._call_ollama(fallback_model, fallback_base_url, prompt, system_instruction)

        if provider == "ollama":
            logger.info(f"Explicitly calling local Ollama ({fallback_model})...")
            return self._call_ollama(fallback_model, fallback_base_url, prompt, system_instruction)

        # Default "auto" logic (Priority: Gemini -> Vertex -> Ollama)
        # 1. Try Google Gemini (AI Studio)
        if self.has_google_key and HAS_GOOGLE_GENAI:
            try:
                logger.info(f"Attempting to call Google Gemini AI Studio ({model_name})...")
                return self._call_gemini(model_name, prompt, system_instruction)
            except Exception as e:
                logger.warning(f"Google Gemini AI Studio call failed: {e}. Trying next provider...")

        # 2. Try Google Vertex AI
        if self.has_vertex_creds and HAS_VERTEX_AI:
            try:
                logger.info(f"Attempting to call Google Vertex AI ({model_name})...")
                return self._call_vertex(model_name, prompt, system_instruction)
            except Exception as e:
                logger.warning(f"Google Vertex AI call failed: {e}. Falling back to local model...")

        # 3. Fallback to Local Ollama
        logger.info(f"Calling local Ollama ({fallback_model})...")
        return self._call_ollama(fallback_model, fallback_base_url, prompt, system_instruction)

    def call_llm_stream(self, prompt: str, task_type: str = "fast", system_instruction: str = None, fallback_model: str = "qwen:14b", fallback_base_url: str = "http://localhost:11434", provider: str = "auto"):
        """
        Stream response from LLM.
        Prioritizes Google Gemini API -> Vertex AI -> Local Ollama.
        """
        model_name = "gemini-1.5-flash" if task_type == "fast" else "gemini-1.5-pro"

        # Explicit Provider Selection
        if provider == "gemini":
            if self.has_google_key and HAS_GOOGLE_GENAI:
                try:
                    logger.info(f"Explicitly streaming from Google Gemini AI Studio ({model_name})...")
                    for chunk in self._call_gemini_stream(model_name, prompt, system_instruction):
                        yield chunk
                    return
                except Exception as e:
                    logger.warning(f"Explicit Google Gemini AI Studio stream failed: {e}. Falling back to Ollama...")
            else:
                 logger.warning("Provider 'gemini' requested but not configured. Falling back to Ollama...")
            # Fallback
            for chunk in self._call_ollama_stream(fallback_model, fallback_base_url, prompt, system_instruction):
                yield chunk
            return

        if provider == "vertex":
            if self.has_vertex_creds and HAS_VERTEX_AI:
                try:
                    logger.info(f"Explicitly streaming from Google Vertex AI ({model_name})...")
                    for chunk in self._call_vertex_stream(model_name, prompt, system_instruction):
                        yield chunk
                    return
                except Exception as e:
                    logger.warning(f"Explicit Google Vertex AI stream failed: {e}. Falling back to Ollama...")
            else:
                 logger.warning("Provider 'vertex' requested but not configured. Falling back to Ollama...")
            # Fallback
            for chunk in self._call_ollama_stream(fallback_model, fallback_base_url, prompt, system_instruction):
                yield chunk
            return

        if provider == "ollama":
            logger.info(f"Explicitly streaming from local Ollama ({fallback_model})...")
            for chunk in self._call_ollama_stream(fallback_model, fallback_base_url, prompt, system_instruction):
                yield chunk
            return

        # Default "auto" logic
        # 1. Try Google Gemini (AI Studio)
        if self.has_google_key and HAS_GOOGLE_GENAI:
            try:
                logger.info(f"Streaming from Google Gemini AI Studio ({model_name})...")
                for chunk in self._call_gemini_stream(model_name, prompt, system_instruction):
                    yield chunk
                return
            except Exception as e:
                logger.warning(f"Google Gemini AI Studio stream failed: {e}. Trying next provider...")

        # 2. Try Google Vertex AI
        if self.has_vertex_creds and HAS_VERTEX_AI:
            try:
                logger.info(f"Streaming from Google Vertex AI ({model_name})...")
                for chunk in self._call_vertex_stream(model_name, prompt, system_instruction):
                    yield chunk
                return
            except Exception as e:
                logger.warning(f"Google Vertex AI stream failed: {e}. Falling back to local model...")

        # 3. Fallback to Local Ollama
        logger.info(f"Streaming from local Ollama ({fallback_model})...")
        for chunk in self._call_ollama_stream(fallback_model, fallback_base_url, prompt, system_instruction):
            yield chunk

    def _call_gemini(self, model_name: str, prompt: str, system_instruction: str = None) -> str:
        """Helper to call Google Gemini API (AI Studio)."""
        generation_config = {
            "temperature": 0.1 if "flash" in model_name else 0.7,
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 8192,
        }

        # Initialize model
        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=generation_config,
            system_instruction=system_instruction
        )

        # Generate content
        response = model.generate_content(prompt)
        return response.text

    def _call_gemini_stream(self, model_name: str, prompt: str, system_instruction: str = None):
        """Helper to stream from Google Gemini API (AI Studio)."""
        generation_config = {
            "temperature": 0.1 if "flash" in model_name else 0.7,
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 8192,
        }

        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=generation_config,
            system_instruction=system_instruction
        )

        response = model.generate_content(prompt, stream=True)
        for chunk in response:
            if chunk.text:
                yield chunk.text

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
