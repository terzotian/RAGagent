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
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)

    # Load .env file explicitly from backend directory
    backend_env = os.path.join(current_dir, ".env")
    load_dotenv(backend_env)
    print(f"DEBUG: Loaded env from {backend_env}")

    # Fallback: Load from project root if not found in backend
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    if not os.path.exists(backend_env):
        root_env = os.path.join(project_root, ".env")
        load_dotenv(root_env)
        print(f"DEBUG: Loaded env from {root_env}")

    soffice_path = "/Applications/LibreOffice.app/Contents/MacOS"
    if soffice_path not in os.environ.get("PATH", ""):
        os.environ["PATH"] = os.environ.get("PATH", "") + os.pathsep + soffice_path

    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # project_root is 'code/backend'
    # we need to add 'code' directory to sys.path to allow 'from backend...'

    # current_dir = code/backend
    # parent = code
    code_dir = os.path.dirname(current_dir)

    if code_dir not in sys.path:
        sys.path.insert(0, code_dir)
        print(f"DEBUG: Added {code_dir} to sys.path")


# Cloud Run environment sets K_SERVICE.
# We should NOT run setup_environment() in Cloud Run because:
# 1. Local libs paths (/Applications/LibreOffice, etc.) don't exist
# 2. It might cause permission errors or path confusion
if not os.getenv("DISABLE_LOCAL_LIBS") and not os.getenv("K_SERVICE"):
    setup_environment()
