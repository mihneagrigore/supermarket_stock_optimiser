import requests
import json
from dotenv import load_dotenv
import os
from PIL import Image
import time

# Load environment variables
BASEDIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASEDIR, '.env'))
API_KEY = os.getenv("API_KEY")

# Resize function
def resize_image(input_path, output_path, width=720, height=1280):
    img = Image.open(input_path)
    resized_img = img.resize((width, height))
    resized_img.save(output_path)
    return output_path

# Function to send image to Tabscanner
def callProcess():
    original_image = "./receipt.jpg"
    resized_image = "./receipt_resized.jpg"

    # Resize the image before sending
    resize_image(original_image, resized_image)

    payload = {
        "documentType": "receipt",
        "decimalPlaces": 3,
        "cents": False,
        "defaultDateParsing": "d/m",
        "region": "gb"
    }

    try:
        with open(resized_image, 'rb') as f:
            response = requests.post(
                "https://api.tabscanner.com/api/2/process",
                files={'file': f},
                data=payload,
                headers={'apikey': API_KEY}
            )

        result = response.json()

        # Save initial JSON response (temporary)
        output_json_path = os.path.join(os.getcwd(), "receipt_data.json")
        with open(output_json_path, "w", encoding="utf-8") as json_file:
            json.dump(result, json_file, indent=2, ensure_ascii=False)

        return result

    finally:
        if os.path.exists(resized_image):
            os.remove(resized_image)

# Function to get processed data using token
def getResultFromToken(token):
    url = f"https://api.tabscanner.com/api/result/{token}"
    headers = {"apikey": API_KEY}

    while True:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()

            if data.get("status") == "processing":
                time.sleep(2)
                continue

            output_json_path = os.path.join(os.getcwd(), f"receipt_result_{token}.json")
            with open(output_json_path, "w", encoding="utf-8") as json_file:
                json.dump(data, json_file, indent=2, ensure_ascii=False)

            temp_json = os.path.join(os.getcwd(), "receipt_data.json")
            if os.path.exists(temp_json):
                os.remove(temp_json)

            return data
        else:
            print(f"Error fetching result: {response.status_code}, {response.text}")
            return None

def normalize_receipt_json(raw_json):
    result = raw_json.get("result", {})

    normalized = {
        "establishment": result.get("establishment"),
        "date": result.get("date"),
        "total": result.get("total"),
        "paymentMethod": result.get("paymentMethod"),
        "lineItems": []
    }

    for item in result.get("lineItems", []):
        line = {
            "descClean": item.get("descClean"),
            "lineTotal": item.get("lineTotal")
        }
        if item.get("unit"):
            line["unit"] = item.get("unit")
        normalized["lineItems"].append(line)

    return normalized

if __name__ == "__main__":
    initial_data = callProcess()

    for i in range(10):
        time.sleep(1)

    token = initial_data.get("token")
    if token:

        print(f"{token}")
        final_result = getResultFromToken(token)

        if final_result:
            normalized_data = normalize_receipt_json(final_result)
            normalized_json_path = os.path.join(os.getcwd(), f"result_{token}.json")

            with open(normalized_json_path, "w", encoding="utf-8") as f:
                json.dump(normalized_data, f, indent=2, ensure_ascii=False)

            os.remove(os.path.join(os.getcwd(), f"receipt_result_{token}.json"))

    else:
        print("No token found in initial response.")
