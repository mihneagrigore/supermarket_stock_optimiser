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
        print(f"No files found matching pattern: {input_pattern}")
        return 0

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
        print("\nErrors encountered:")
        for error in errors:
            print(f"  - {error}")

    # Write merged data to output file
    if merged_data:
        output_path = script_dir / output_file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, indent=2, ensure_ascii=False)

        exit(0)

        # Print some statistics
        total_amount = sum(receipt.get('total', 0) for receipt in merged_data)
        total_products = sum(len(receipt.get('products', [])) for receipt in merged_data)
        supermarkets = set(receipt.get('supermarket') for receipt in merged_data if receipt.get('supermarket'))

    else:
        exit(1)

    return len(merged_data)


if __name__ == "__main__":
    merge_json_results()
