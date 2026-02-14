import os
import asyncio
from backend.root_path import PROJECT_ROOT
from backend.model.rag_indexer import ingest_file

KB_ROOT = os.path.join(PROJECT_ROOT, "knowledge_base")

async def reindex_all():
    print(f"Starting comprehensive reindexing from {KB_ROOT}")
    
    if not os.path.exists(KB_ROOT):
        print(f"Knowledge base root not found: {KB_ROOT}")
        return

    # 1. Public Policies
    public_policies_dir = os.path.join(KB_ROOT, "public", "policies")
    if os.path.exists(public_policies_dir):
        print("Indexing Public Policies...")
        files = [f for f in os.listdir(public_policies_dir) if f != ".DS_Store"]
        for f in files:
            file_path = os.path.join(public_policies_dir, f)
            await ingest_file("public", file_path)

    # 2. Courses
    # Directories starting with course_
    for item in os.listdir(KB_ROOT):
        if item.startswith("course_") and os.path.isdir(os.path.join(KB_ROOT, item)):
            course_code = item # e.g. course_COMP101 or just course_... wait, upload uses f"course_{code}" as dir name?
            # upload_course_file: locate_path("knowledge_base", f"course_{code}", "files")
            # So dir is knowledge_base/course_{code}
            
            files_dir = os.path.join(KB_ROOT, item, "files")
            if os.path.exists(files_dir):
                print(f"Indexing Course {item}...")
                files = [f for f in os.listdir(files_dir) if f != ".DS_Store"]
                for f in files:
                    file_path = os.path.join(files_dir, f)
                    await ingest_file(item, file_path) # base is item name (course_{code})

    # 3. User Assignments
    # Directory: users/{user_id}/assignments
    users_dir = os.path.join(KB_ROOT, "users")
    if os.path.exists(users_dir):
        print("Indexing User Assignments...")
        for user_id in os.listdir(users_dir):
            user_path = os.path.join(users_dir, user_id)
            if os.path.isdir(user_path):
                assign_dir = os.path.join(user_path, "assignments")
                if os.path.exists(assign_dir):
                    files = [f for f in os.listdir(assign_dir) if f != ".DS_Store"]
                    for f in files:
                        file_path = os.path.join(assign_dir, f)
                        # Base: user_{user_id}_private
                        base_name = f"user_{user_id}_private"
                        await ingest_file(base_name, file_path)

    print("Reindexing complete.")

if __name__ == "__main__":
    asyncio.run(reindex_all())
