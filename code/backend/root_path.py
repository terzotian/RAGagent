import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

POLICIES_DIR = os.path.join(PROJECT_ROOT, "knowledge_base", "public", "policies")
PIECES_DIR = os.path.join(PROJECT_ROOT, "knowledge_base", "public", "pieces")


def locate_path(*subdirs):
    """
    按需拼接 PROJECT_ROOT 下的任意子目录。
    例： locate_path('knowledge_base', 'lingnan','pieces') → PIECES_DIR
    """
    return os.path.join(PROJECT_ROOT, *subdirs)


def policy_file(base, filename: str):
    return os.path.join(PROJECT_ROOT, "knowledge_base", base, "policies", filename)


def piece_file(base, filename: str):
    return os.path.join(PROJECT_ROOT, "knowledge_base", base, "pieces", filename)


def piece_dir(base: str):
    return os.path.join(PROJECT_ROOT, "knowledge_base", base, "pieces")


def course_file(base: str, filename: str):
    return os.path.join(PROJECT_ROOT, "knowledge_base", base, "files", filename)


def user_assignment_file(user_id: int, filename: str):
    return os.path.join(PROJECT_ROOT, "knowledge_base", "users", str(user_id), "assignments", filename)
