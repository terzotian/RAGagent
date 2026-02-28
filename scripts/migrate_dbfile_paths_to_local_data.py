import argparse
import os
import sys

# Add project root and code directory to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)
sys.path.append(os.path.join(root_dir, "code"))

from backend.database.connection import SessionLocal
from backend.database.models import DBFile
from backend.root_path import resolve_storage_path


def migrate(dry_run: bool) -> int:
    db = SessionLocal()
    updated = 0
    skipped_same = 0
    skipped_missing = 0
    skipped_empty = 0

    try:
        files = db.query(DBFile).all()
        print(f"Found {len(files)} DBFile rows")

        for row in files:
            old_path = row.file_path
            if not old_path:
                skipped_empty += 1
                continue

            new_path = resolve_storage_path(old_path)

            if new_path == old_path:
                skipped_same += 1
                continue

            # Safety: only update when the new resolved path exists.
            if not os.path.exists(new_path):
                skipped_missing += 1
                continue

            print(f"UPDATE file_id={row.file_id}:\n  {old_path}\n  -> {new_path}")
            if not dry_run:
                row.file_path = new_path
                updated += 1

        if dry_run:
            print("Dry-run mode: no database changes were written.")
        else:
            db.commit()
            print(f"Committed updates: {updated}")

        print(
            "Summary:\n"
            f"  updated={updated}\n"
            f"  skipped_same={skipped_same}\n"
            f"  skipped_missing_new_path={skipped_missing}\n"
            f"  skipped_empty={skipped_empty}"
        )

        return 0

    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate DBFile.file_path to .local_data absolute paths")
    parser.add_argument("--dry-run", action="store_true", help="Print planned updates without committing")
    args = parser.parse_args()

    return migrate(dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
