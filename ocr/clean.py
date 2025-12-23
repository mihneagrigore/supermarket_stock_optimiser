import os
import glob
import json

def clean_result_files():
    """Clean all result_*.json and merged_*.json files in the current directory."""

    # Find all files matching the patterns result_*.json and merged_*.json
    files = glob.glob("result_*.json") + glob.glob("merged_*.json")

    if not files:
        return

    deleted_count = 0
    for file in files:
        try:
            os.remove(file)
            deleted_count += 1
        except Exception as e:
            return -1

    return deleted_count

if __name__ == "__main__":
    if clean_result_files() == -1:
        exit(1)

    exit(0)

