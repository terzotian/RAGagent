
import os
import sys
from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel
from vertexai.language_models import TextEmbeddingModel

# Load environment variables
load_dotenv(dotenv_path="code/backend/.env")

project_id = os.getenv("VERTEX_PROJECT_ID")
location = os.getenv("VERTEX_LOCATION", "asia-southeast1")
credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

print(f"Project ID: {project_id}")
print(f"Location: {location}")
print(f"Credentials: {credentials_path}")

try:
    vertexai.init(project=project_id, location=location)
    print(f"Vertex AI initialized successfully in {location}.")

    # 1. Test Embedding Model (Known to work previously)
    try:
        print("\nTesting Embedding Model 'text-embedding-004':")
        embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-004")
        embeddings = embedding_model.get_embeddings(["Hello world"])
        print(f"✅ Embedding Model 'text-embedding-004' is AVAILABLE. Vector length: {len(embeddings[0].values)}")
    except Exception as e:
        print(f"❌ Embedding Model 'text-embedding-004' is UNAVAILABLE. Error: {e}")

    # 2. Test Generative Models (Newer versions)
    models_to_test = [
        "gemini-2.0-flash-001",
        "gemini-2.0-flash",
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-2.0-pro-exp", # Just in case
        "gemini-1.5-flash-002", # Might still be active until Sept 2025? No, today is 2026.
    ]

    print("\nTesting model availability:")
    for model_name in models_to_test:
        try:
            model = GenerativeModel(model_name)
            response = model.generate_content("Hello, are you available?")
            print(f"✅ Model '{model_name}' is AVAILABLE. Response: {response.text.strip()}")
        except Exception as e:
            print(f"❌ Model '{model_name}' is UNAVAILABLE. Error: {e}")

except Exception as e:
    print(f"Failed to initialize Vertex AI: {e}")
