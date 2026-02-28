import sys
import os
from dotenv import load_dotenv


def setup_environment():
    """
    Configure environment variables and python path for local development.
    Includes:
    - Load .env from project root
    - LibreOffice: For document conversion
    - Project root: For module resolution
    """
    # Define key directories with clear names
    # current_dir: .../code/backend
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    # code_dir: .../code (Parent of backend, acting as package root)
    code_dir = os.path.dirname(backend_dir)
    # repo_root: .../AgenticRAG (Git repository root)
    repo_root = os.path.dirname(code_dir)

    # 1. Load .env file (Prioritize backend/.env)
    backend_env = os.path.join(backend_dir, ".env")
    repo_env = os.path.join(repo_root, ".env")

    if os.path.exists(backend_env):
        load_dotenv(backend_env)
        print(f"DEBUG: Loaded env from {backend_env}")
    elif os.path.exists(repo_env):
        load_dotenv(repo_env)
        print(f"DEBUG: Loaded env from {repo_env}")
    else:
        print("WARNING: No .env file found in backend or repo root.")

    # 2. Configure Python Path
    # Add 'code' directory to sys.path to allow 'from backend...' imports
    # This is the most standard way to structure imports
    if code_dir not in sys.path:
        sys.path.insert(0, code_dir)
        print(f"DEBUG: Added {code_dir} to sys.path")

    # Add repo_root only if absolutely necessary for scripts outside 'code'
    # but generally 'code' dir is enough for backend modules.
    if repo_root not in sys.path:
         sys.path.insert(1, repo_root) # Insert at 1 to keep code_dir higher priority

    # 3. Configure LibreOffice Path
    soffice_path = "/Applications/LibreOffice.app/Contents/MacOS"
    if soffice_path not in os.environ.get("PATH", ""):
        os.environ["PATH"] = os.environ.get("PATH", "") + os.pathsep + soffice_path



# Cloud Run environment sets K_SERVICE.
# We should NOT run setup_environment() in Cloud Run because:
# 1. Local libs paths (/Applications/LibreOffice, etc.) don't exist
# 2. It might cause permission errors or path confusion
if not os.getenv("DISABLE_LOCAL_LIBS") and not os.getenv("K_SERVICE"):
    setup_environment()
