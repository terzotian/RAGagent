import sys
import os

def setup_environment():
    """
    Configure environment variables and python path for local dependencies.
    Includes:
    - code/libs: For local python packages (LightRAG, Mineru)
    - code/libs/bin: For Mineru binaries
    - LibreOffice: For document conversion
    - Project root: For module resolution
    """
    # Base paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir) # code/
    libs_path = os.path.join(project_root, 'libs')

    # 1. Add libs to sys.path
    if libs_path not in sys.path:
        sys.path.insert(0, libs_path)

    # 2. Add libs/bin to PATH
    libs_bin_path = os.path.join(libs_path, 'bin')
    if libs_bin_path not in os.environ["PATH"]:
        os.environ["PATH"] += os.pathsep + libs_bin_path

    # 3. Add LibreOffice to PATH
    soffice_path = "/Applications/LibreOffice.app/Contents/MacOS"
    if soffice_path not in os.environ["PATH"]:
        os.environ["PATH"] += os.pathsep + soffice_path

    # 4. Add project root to sys.path
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

# Execute setup
setup_environment()
