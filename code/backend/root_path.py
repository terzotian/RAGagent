import os

# Code root (this folder: .../code/backend)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Repo root: .../AgenticRAG
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Runtime data root. Default to repo-level .local_data for clean separation.
# Override with LOCAL_DATA_DIR for custom layouts.
DATA_ROOT = os.getenv("LOCAL_DATA_DIR") or os.path.join(REPO_ROOT, ".local_data")

KB_ROOT = os.path.join(DATA_ROOT, "knowledge_base")
UPLOADS_ROOT = os.path.join(DATA_ROOT, "uploads")
AVATARS_ROOT = os.path.join(DATA_ROOT, "avatars")

POLICIES_DIR = os.path.join(KB_ROOT, "public", "policies")
PIECES_DIR = os.path.join(KB_ROOT, "public", "pieces")


def locate_path(*subdirs):
    """
    按需拼接 KB_ROOT 下的任意子目录（数据目录）。
    例： locate_path('public', 'pieces') → PIECES_DIR
    """
    return os.path.join(KB_ROOT, *subdirs)


def resolve_storage_path(path: str) -> str:
    """Resolve a stored file path to the current local absolute path.

    Historically, the project stored relative paths like:
    - knowledge_base/public/policies/...
    - backend/knowledge_base/public/policies/...
    - code/backend/knowledge_base/public/policies/...

    After migrating runtime data to repo-level `.local_data/knowledge_base`,
    these should map to KB_ROOT.
    """
    if not path:
        return path

    # Handle legacy absolute paths pointing to the old code-root data layout.
    if os.path.isabs(path):
        normalized_abs = path.replace("\\", "/")
        legacy_abs_markers = (
            "/code/backend/knowledge_base/",
            "/backend/knowledge_base/",
            "/knowledge_base/",
        )
        for marker in legacy_abs_markers:
            if marker in normalized_abs:
                suffix = normalized_abs.split(marker, 1)[1]
                return os.path.join(KB_ROOT, suffix)
        return path

    normalized = path.replace("\\", "/").lstrip("/")

    legacy_prefixes = (
        "code/backend/knowledge_base/",
        "backend/knowledge_base/",
        "knowledge_base/",
    )
    for prefix in legacy_prefixes:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
            break

    return os.path.join(KB_ROOT, normalized)


def policy_file(base, filename: str):
    return os.path.join(KB_ROOT, base, "policies", filename)


def piece_file(base, filename: str):
    return os.path.join(KB_ROOT, base, "pieces", filename)


def piece_dir(base: str):
    return os.path.join(KB_ROOT, base, "pieces")


def course_file(base: str, filename: str):
    return os.path.join(KB_ROOT, base, "files", filename)


def user_assignment_file(user_id: int, filename: str):
    return os.path.join(KB_ROOT, "users", str(user_id), "assignments", filename)


def uploads_dir(*subdirs: str) -> str:
    """Runtime uploads directory under DATA_ROOT/uploads."""
    return os.path.join(UPLOADS_ROOT, *subdirs)


def avatars_dir(*subdirs: str) -> str:
    """User avatars directory under DATA_ROOT/avatars."""
    return os.path.join(AVATARS_ROOT, *subdirs)
