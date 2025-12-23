#!/usr/bin/env python3
"""
Fetch company details and balances from OpenAPI.ro based on TAX_CODE.
Outputs a flattened JSON file with combined data.

Usage:
    python request.py
Return:
    1 on success, 0 on failure.
"""

import requests
import os
import json
import sys
import logging
from datetime import datetime
from typing import Any, Dict
from dotenv import load_dotenv
import unicodedata
from pathlib import Path

load_dotenv()

# Configure logging for production
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)

BASE_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = BASE_DIR / "frontend"
FIRMS_DIR = BASE_DIR.parent / "data" / "company-details"


def remove_diacritics(text: str) -> str:
    if not isinstance(text, str):
        return text
    normalized = unicodedata.normalize("NFD", text)
    return "".join(c for c in normalized if unicodedata.category(c) != "Mn")


def flatten(prefix: str, obj: Any, out: Dict[str, Any]) -> None:
    """
    Recursively flatten nested dictionaries and lists.

    Args:
        prefix (str): Prefix for nested keys.
        obj (Any): The current object to flatten (dict, list, or primitive).
        out (dict): Output dictionary to store flattened results.
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            flatten(f"{prefix}_{k}" if prefix else k, v, out)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            flatten(f"{prefix}_{i}", item, out)
    else:
        out[prefix] = obj


def fetch_json(url: str, headers: Dict[str, str]) -> dict:
    """
    Fetch JSON from a URL with error handling.

    Args:
        url (str): API endpoint.
        headers (dict): HTTP headers.

    Returns:
        dict: Parsed JSON response, empty dict on failure.
    """
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise for HTTP errors
        return response.json()
    except (requests.RequestException, json.JSONDecodeError) as e:
        logging.warning(f"Failed to fetch {url}: {e}")
        return {}


def main() -> int:
    """Main entry point of the script."""

    # with open(FORM_JSON_PATH, "r", encoding="utf-8") as f:
    #     user_json = json.load(f)

    # Your form structure is: { "data": { ...fields... } }
    # user_data = user_json.get("data", {})
    TAX_CODE = input("Enter TAX_CODE (CUI): ").strip()

    if not TAX_CODE:
        logging.error("ERROR: TAX_CODE cannot be empty")
        return 0

    logging.info(f"Using CUI: {TAX_CODE}")

    OPENAPI_KEY = os.getenv("API_KEY")

    BASE_URL = "https://api.openapi.ro/api/companies/{tax_code}/"
    BASE_URL_COMPLETE = (
        "https://api.openapi.ro/api/companies/{tax_code}/balances/{year}"
    )
    headers = {"x-api-key": OPENAPI_KEY}

    # Step 1: Fetch basic company info
    logging.info(f"Fetching company info for TAX_CODE={TAX_CODE}")
    company_data = fetch_json(BASE_URL.format(tax_code=TAX_CODE), headers)
    if not company_data or "error" in company_data:
        logging.error("Failed to fetch valid company data.")
        return 0

    # Step 2: Fetch balances for last 5 years
    current_year = datetime.now().year
    balances_data = {}
    for i in range(5):
        year = current_year - i
        logging.info(f"Attempting to fetch balances for year {year}")
        data = fetch_json(
            BASE_URL_COMPLETE.format(tax_code=TAX_CODE, year=year), headers
        )
        if data and "error" not in data:
            balances_data = data
            logging.info(f"Balances found for year {year}")
            break

    if not balances_data:
        logging.error("No valid balances data found for the last 5 years.")
        return 0

    # Step 3: Flatten and merge data
    flattened_data = {}
    for k, v in company_data.items():
        if k != "meta":
            flatten(k, v, flattened_data)

    if "data" in balances_data:
        for k, v in balances_data["data"].items():
            flatten(k, v, flattened_data)

    for k in ["year", "balance_type", "caen_code"]:
        if k in balances_data:
            flattened_data[k] = balances_data[k]

    # Always include TAX_CODE / CUI
    flattened_data["cui"] = TAX_CODE

    cleaned_output = {}
    for key, value in flattened_data.items():
        new_key = remove_diacritics(key)
        if isinstance(value, str):
            cleaned_output[new_key] = remove_diacritics(value)
        else:
            cleaned_output[new_key] = value

    output_data = cleaned_output

    details_filename = FIRMS_DIR / f"{TAX_CODE}.json"

    # Step 4: Save to JSON file
    try:
        with open(details_filename, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
        logging.info(f"Data saved to {details_filename}")
    except Exception as e:
        logging.error(f"Failed to save JSON file: {e}")
        return 0

    return 1


if __name__ == "__main__":
    result = main()
    sys.exit(0 if result == 1 else 1)