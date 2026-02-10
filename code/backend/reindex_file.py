
import asyncio
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add libs to path
libs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../libs'))
if libs_path not in sys.path:
    sys.path.insert(0, libs_path)

# Add libs/bin to PATH for mineru command
libs_bin_path = os.path.join(libs_path, 'bin')
if libs_bin_path not in os.environ["PATH"]:
    os.environ["PATH"] += os.pathsep + libs_bin_path

# Add LibreOffice to PATH
soffice_path = "/Applications/LibreOffice.app/Contents/MacOS"
if soffice_path not in os.environ["PATH"]:
    os.environ["PATH"] += os.pathsep + soffice_path

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
# Add project root to path for raganything
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from backend.main import DATABASE_URL, DBFile
from backend.model.rag_indexer import ingest_file

async def main():
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    # Find the file
    search_term = sys.argv[1] if len(sys.argv) > 1 else '%Spotify%'
    file = db.query(DBFile).filter(DBFile.file_name.like(f'%{search_term}%')).first()
    if not file:
        print("File not found")
        return

    print(f"Indexing file: {file.file_name}")
    print(f"Path: {file.file_path}")
    print(f"Base: {file.base}")

    if not os.path.exists(file.file_path):
        print("File does not exist on disk!")
        return

    await ingest_file(file.base, file.file_path)
    print("Indexing complete!")

    db.close()

if __name__ == "__main__":
    asyncio.run(main())
