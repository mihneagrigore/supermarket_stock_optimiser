import json
import glob
import os
from pathlib import Path


def merge_json_results(input_pattern="result_*.json", output_file="merged_results.json"):
    """
    Merge all JSON files matching the input pattern into a single JSON file.

    Args:
        input_pattern: Glob pattern to match input files (default: "result_*.json")
        output_file: Name of the output merged file (default: "merged_results.json")

    Returns:
        Number of files merged
    """
    # Get the directory of this script
    script_dir = Path(__file__).parent

    # Find all matching JSON files
    json_files = glob.glob(str(script_dir / input_pattern))

    if not json_files:
        exit(0)

    # Read and collect all JSON data
    merged_data = []
    errors = []

    for json_file in sorted(json_files):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                merged_data.append(data)
        except json.JSONDecodeError as e:
            errors.append(f"Error parsing {os.path.basename(json_file)}: {e}")
        except Exception as e:
            errors.append(f"Error reading {os.path.basename(json_file)}: {e}")

    # Report any errors
    if errors:
        exit(1)

    # Write merged data to output file
    if merged_data:
        output_path = script_dir / output_file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, indent=2, ensure_ascii=False)

        # Delete input files after successful merge
        for json_file in json_files:
            try:
                os.remove(json_file)
            except Exception as e:
                exit(1)

    else:
        exit(1)

    return len(merged_data)


if __name__ == "__main__":
    merge_json_results()
    exit(0)
