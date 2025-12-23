import requests
import json
from dotenv import load_dotenv
import os
from PIL import Image
import time

# Load environment variables
BASEDIR = os.path.abspath(os.path.dirname(__file__))

# Get the API key from tabscanner.com and set it in a .env file
load_dotenv(os.path.join(BASEDIR, '.env'))
API_KEY = os.getenv("API_KEY")
if not API_KEY or not API_KEY.strip():
    raise RuntimeError(
        "API_KEY environment variable is not set or is empty. "
        "Please define API_KEY in your environment or in the .env file."
    )

# Resize the image to specified dimensions for better processing
def resize_image(input_path, output_path, width=720, height=1280):
    try:
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input image file not found: {input_path}")

        img = Image.open(input_path)
        resized_img = img.resize((width, height))
        resized_img.save(output_path)
        return output_path
    except FileNotFoundError as e:
        print(f"Error: {e}")
        raise
    except IOError as e:
        print(f"Error opening or processing image file '{input_path}': {e}")
        raise
    except Exception as e:
        print(f"Unexpected error during image resizing: {e}")
        raise

# Function to send image to Tabscanner
def callProcess():
    original_image = "./receipt.jpg"
    resized_image = "./receipt_resized.jpg"

    try:
        # Resize the image before sending
        resize_image(original_image, resized_image)
    except Exception as e:
        print(f"Failed to resize image: {e}")
        return None

    payload = {
        "documentType": "receipt",
        "decimalPlaces": 3,
        "cents": False,
        "defaultDateParsing": "d/m",
        "region": "gb"
    }

    try:
        if not os.path.exists(resized_image):
            raise FileNotFoundError(f"Resized image file not found: {resized_image}")

        with open(resized_image, 'rb') as f:
            response = requests.post(
                "https://api.tabscanner.com/api/2/process",
                files={'file': f},
                data=payload,
                headers={'apikey': API_KEY}
            )

        response.raise_for_status()
        result = response.json()

        # Save initial JSON response (temporary)
        output_json_path = os.path.join(os.getcwd(), "receipt_data.json")
        try:
            with open(output_json_path, "w", encoding="utf-8") as json_file:
                json.dump(result, json_file, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Warning: Could not save temporary JSON file: {e}")

        return result

    except FileNotFoundError as e:
        print(f"Error: {e}")
        return None
    except IOError as e:
        print(f"Error reading resized image file: {e}")
        return None
    except requests.RequestException as e:
        print(f"API request error: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing API response: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error during API call: {e}")
        return None
    finally:
        if os.path.exists(resized_image):
            try:
                os.remove(resized_image)
            except OSError as e:
                print(f"Warning: Could not remove temporary resized image: {e}")

# Function to get processed data using token
def getResultFromToken(token, max_retries=60, retry_interval=2):
    """
    Poll the API for processed results with timeout protection.

    Args:
        token: The processing token from the initial API call
        max_retries: Maximum number of polling attempts (default: 60, ~2 minutes)
        retry_interval: Seconds to wait between retries (default: 2)

    Returns:
        Processed data dict or None if failed/timed out
    """
    url = f"https://api.tabscanner.com/api/result/{token}"
    headers = {"apikey": API_KEY}
    retry_count = 0

    while retry_count < max_retries:
        try:
            response = requests.get(url, headers=headers)
        except requests.RequestException as e:
            print(f"Network error while fetching result for token {token}: {e}")
            return None

        if response.status_code == 200:
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON response: {e}")
                return None

            if data.get("status") == "processing":
                retry_count += 1
                if retry_count >= max_retries:
                    print(f"Timeout: Processing did not complete after {max_retries} attempts ({max_retries * retry_interval} seconds)")
                    return None
                time.sleep(retry_interval)
                continue

            output_json_path = os.path.join(os.getcwd(), f"receipt_result_{token}.json")
            try:
                with open(output_json_path, "w", encoding="utf-8") as json_file:
                    json.dump(data, json_file, indent=2, ensure_ascii=False)
            except IOError as e:
                print(f"Warning: Could not save result JSON file: {e}")

            temp_json = os.path.join(os.getcwd(), "receipt_data.json")
            if os.path.exists(temp_json):
                try:
                    os.remove(temp_json)
                except OSError as e:
                    print(f"Warning: Could not remove temporary JSON file: {e}")

            return data
        else:
            print(f"Error fetching result: {response.status_code}, {response.text}")
            return None

    print(f"Timeout: Maximum retry limit ({max_retries}) reached")
    return None

def normalize_receipt_json(raw_json):
    result = raw_json.get("result", {})

    normalized = {
        "supermarket": result.get("establishment"),
        "date": result.get("date"),
        "total": result.get("total"),
        "paymentMethod": result.get("paymentMethod"),
        "products": []
    }

    for item in result.get("lineItems", []):
        line = {
            "productName": item.get("descClean"),
            "productPrice": item.get("lineTotal")
        }
        if item.get("unit"):
            line["unit"] = item.get("unit")
        normalized["products"].append(line)
    return normalized

if __name__ == "__main__":
    initial_data = callProcess()

    if initial_data is None:
        print("Failed to process initial image. Exiting.")
        exit(1)

    for i in range(10):
        time.sleep(1)

    token = initial_data.get("token")
    if token:

        print(f"{token}")
        final_result = getResultFromToken(token)

        if final_result:
            normalized_data = normalize_receipt_json(final_result)
            normalized_json_path = os.path.join(os.getcwd(), f"result_{token}.json")

            try:
                with open(normalized_json_path, "w", encoding="utf-8") as f:
                    json.dump(normalized_data, f, indent=2, ensure_ascii=False)
            except IOError as e:
                print(f"Error saving normalized result: {e}")

            receipt_result_path = os.path.join(os.getcwd(), f"receipt_result_{token}.json")
            if os.path.exists(receipt_result_path):
                try:
                    os.remove(receipt_result_path)
                except OSError as e:
                    print(f"Warning: Could not remove receipt result file: {e}")

    else:
        print("No token found in initial response.")
