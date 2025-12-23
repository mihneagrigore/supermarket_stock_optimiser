import os
import glob
import json

def clean_result_files():
    """Clean all result_*.json files in the current directory."""
    # Find all files matching the pattern result_*.json
    pattern = "result_*.json"
    files = glob.glob(pattern)

    if not files:
        print("No result_*.json files found in the current directory.")
        return

    print(f"Found {len(files)} file(s) to clean:")
    for file in files:
        print(f"  - {file}")

    deleted_count = 0
    for file in files:
        try:
            os.remove(file)
            print(f"Deleted: {file}")
            deleted_count += 1
        except Exception as e:
            print(f"Error deleting {file}: {e}")
            return -1

    print(f"\nSuccessfully deleted {deleted_count} file(s).")

    return deleted_count

if __name__ == "__main__":
    if clean_result_files() == -1:
        exit(1)

    exit(0)

