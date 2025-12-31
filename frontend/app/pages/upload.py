from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
import os
import sys
import json
import uuid
import subprocess
from werkzeug.utils import secure_filename
import pandas as pd
from datetime import datetime
import logging
import sqlite3

logger = logging.getLogger(__name__)

upload_pages = Blueprint("upload", __name__)

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "../../../temp_uploads")
ALLOWED_RECEIPT_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}
ALLOWED_CSV_EXTENSIONS = {'csv'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def get_company_name(email):
    """Fetch company name from database"""
    if not email:
        return None
    db_path = os.path.join(os.path.dirname(__file__), "../../../backend/clients/clients.db")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT denumire FROM clients WHERE email = ?", (email,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        print(f"Error fetching company name: {e}")
        return None

@upload_pages.route("/upload")
def upload():
    """Main upload page - requires authentication"""
    if "user_email" not in session:
        flash("Please login to access the upload", "error")
        return redirect(url_for("login.login"))

    # Get receipt count from session
    receipt_count = len(session.get("uploaded_receipts", []))
    user_email = session.get("user_email")
    company_name = get_company_name(user_email)

    return render_template(
        "upload.html",
        user_email=user_email,
        company_name=company_name,
        receipt_count=receipt_count
    )

@upload_pages.route("/upload/upload_receipt", methods=["POST"])
def upload_receipt():
    """Handle individual receipt upload - stores temporarily until save"""
    if "user_email" not in session:
        return jsonify({"success": False, "error": "Not authenticated"}), 401

    if 'receipt' not in request.files:
        return jsonify({"success": False, "error": "No file provided"}), 400

    file = request.files['receipt']

    if file.filename == '':
        return jsonify({"success": False, "error": "Empty filename"}), 400

    if not allowed_file(file.filename, ALLOWED_RECEIPT_EXTENSIONS):
        return jsonify({"success": False, "error": "Invalid file type"}), 400

    try:
        # Generate unique ID for this receipt
        receipt_id = str(uuid.uuid4())
        filename = secure_filename(f"{receipt_id}_{file.filename}")
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        # Save file temporarily
        file.save(filepath)

        # Store receipt info in session
        if "uploaded_receipts" not in session:
            session["uploaded_receipts"] = []

        receipt_info = {
            "id": receipt_id,
            "filename": filename,
            "original_name": file.filename,
            "filepath": filepath,
            "uploaded_at": datetime.now().isoformat()
        }

        session["uploaded_receipts"].append(receipt_info)
        session.modified = True

        return jsonify({
            "success": True,
            "receipt_id": receipt_id,
            "filename": file.filename
        })

    except Exception as e:
        logger.exception("Error while uploading receipt")
        return jsonify({"success": False, "error": "Internal server error"}), 500

@upload_pages.route("/upload/save_receipts", methods=["POST"])
def save_receipts():
    """Process all uploaded receipts using OCR and save results"""
    if "user_email" not in session:
        return jsonify({"success": False, "error": "Not authenticated"}), 401

    try:
        data = request.get_json()
        receipt_ids = data.get("receipt_ids", [])

        uploaded_receipts = session.get("uploaded_receipts", [])
        receipts_to_process = [r for r in uploaded_receipts if r["id"] in receipt_ids]

        if not receipts_to_process:
            return jsonify({"success": False, "error": "No receipts to process"}), 400

        # Process each receipt through OCR
        processed_results = []

        for receipt in receipts_to_process:
            result = process_receipt_ocr(receipt["filepath"])
            if result:
                processed_results.append({
                    "receipt_id": receipt["id"],
                    "original_name": receipt["original_name"],
                    "data": result
                })

        # Save all processed receipts to a consolidated file
        results_dir = os.path.join(os.path.dirname(__file__), "../../../data/processed_receipts")
        os.makedirs(results_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        user_email = session.get("user_email", "unknown").replace("@", "_at_")
        results_file = os.path.join(results_dir, f"receipts_{user_email}_{timestamp}.json")

        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(processed_results, f, indent=2, ensure_ascii=False)

        # Clean up temp files
        for receipt in receipts_to_process:
            try:
                if os.path.exists(receipt["filepath"]):
                    os.remove(receipt["filepath"])
            except Exception as e:
                print(f"Error removing temp file: {e}")

        # Clear session receipts
        session["uploaded_receipts"] = []
        session.modified = True

        return jsonify({
            "success": True,
            "count": len(processed_results),
            "results_file": results_file
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

def process_receipt_ocr(image_path):
    """Process a single receipt using the OCR system"""
    try:
        # Import OCR functions
        ocr_dir = os.path.join(os.path.dirname(__file__), "../../../ocr")
        sys.path.insert(0, ocr_dir)

        # We'll create a simplified version that uses the OCR main.py logic
        # Copy the image to the OCR directory as receipt.jpg
        ocr_receipt_path = os.path.join(ocr_dir, "receipt.jpg")

        from PIL import Image
        img = Image.open(image_path)
        img.save(ocr_receipt_path)

        # Run the OCR main script
        script_path = os.path.join(ocr_dir, "main.py")
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            cwd=ocr_dir
        )

        if result.returncode == 0:
            # Find the result JSON file (result_*.json)
            result_files = [f for f in os.listdir(ocr_dir) if f.startswith("result_") and f.endswith(".json")]

            if result_files:
                latest_result = max(result_files, key=lambda f: os.path.getctime(os.path.join(ocr_dir, f)))
                result_path = os.path.join(ocr_dir, latest_result)

                with open(result_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Clean up OCR result files
                os.remove(result_path)
                if os.path.exists(ocr_receipt_path):
                    os.remove(ocr_receipt_path)

                return data

        return None

    except Exception as e:
        print(f"Error processing receipt OCR: {e}")
        return None

@upload_pages.route("/upload/upload_csv", methods=["POST"])
def upload_csv():
    """Handle CSV upload and process with ML predictions for all products"""
    if "user_email" not in session:
        flash("Please login to access this feature", "error")
        return redirect(url_for("login.login"))

    if 'csv_file' not in request.files:
        flash("No file uploaded", "error")
        return redirect(url_for("upload.upload"))

    file = request.files['csv_file']

    if file.filename == '':
        flash("Empty filename", "error")
        return redirect(url_for("upload.upload"))

    if not allowed_file(file.filename, ALLOWED_CSV_EXTENSIONS):
        flash("Invalid file type. Please upload a CSV file", "error")
        return redirect(url_for("upload.upload"))

    try:
        # Read CSV
        df = pd.read_csv(file)

        # Save DataFrame as pickle for future reference
        user_email = session.get("user_email", "unknown")
        pickle_path = os.path.join(UPLOAD_FOLDER, f"{user_email}_csv.pkl")
        df.to_pickle(pickle_path)

        # Get client_id for database import
        client_id = get_client_id_by_email(user_email)

        # Import CSV into database if client_id exists
        if client_id:
            try:
                # Save temp file for database import
                temp_csv = os.path.join(UPLOAD_FOLDER, "temp_import.csv")
                df.to_csv(temp_csv, index=False)
                import_to_database(temp_csv, client_id)
                os.remove(temp_csv)
            except Exception as e:
                flash(f"Database import warning: {str(e)}", "warning")

        # Import ML prediction function
        ml_dir = os.path.join(os.path.dirname(__file__), "../../../ml")
        sys.path.insert(0, ml_dir)
        sys.path.insert(0, os.path.join(ml_dir, "src"))

        from src.predict import predict_all_products_from_csv

        # Run predictions for all products
        prediction_data = predict_all_products_from_csv(df)

        # Check for errors
        if "error" in prediction_data:
            flash(f"Prediction error: {prediction_data['error']}", "error")
            return redirect(url_for("upload.upload"))

        # Save prediction results as pickle
        import pickle
        predictions_path = os.path.join(UPLOAD_FOLDER, f"{user_email}_predictions.pkl")
        with open(predictions_path, 'wb') as f:
            pickle.dump(prediction_data, f)

        # Flash success message
        num_products = len(prediction_data['predictions'])
        num_skipped = len(prediction_data['skipped_products'])

        if num_products > 0:
            flash(f"CSV processed successfully! Predictions generated for {num_products} product(s).", "success")
            if num_skipped > 0:
                flash(f"{num_skipped} product(s) skipped due to insufficient data.", "warning")
        else:
            flash("No predictions could be generated. Please check your data.", "error")

        # Redirect to dashboard to view results
        return redirect(url_for("dashboard.dashboard"))

    except Exception as e:
        flash(f"Error processing CSV: {str(e)}", "error")
        import traceback
        traceback.print_exc()
        return redirect(url_for("upload.upload"))

def get_client_id_by_email(email):
    """Get client ID from clients.db by email"""
    import sqlite3
    clients_db_path = os.path.join(os.path.dirname(__file__), "../../../backend/clients/clients.db")

    if not os.path.exists(clients_db_path):
        return None

    try:
        conn = sqlite3.connect(clients_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM clients WHERE email = ?", (email,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        print(f"Error fetching client ID: {e}")
        return None

def import_to_database(csv_path, client_id):
    """Import CSV data to products.db using the csv-import.py script"""
    try:
        database_dir = os.path.join(os.path.dirname(__file__), "../../../database")
        import_script = os.path.join(database_dir, "csv-import.py")
        db_path = os.path.join(database_dir, "products.db")

        # Run the import script with the correct argument order: --csv <path> --db <path> <client_id>
        result = subprocess.run(
            [sys.executable, import_script, "--csv", csv_path, "--db", db_path, str(client_id)],
            capture_output=True,
            text=True,
            cwd=database_dir
        )

        if result.returncode != 0:
            raise Exception(f"Database import failed: {result.stderr}")

        print(f"Database import output: {result.stdout}")
        return True

    except Exception as e:
        print(f"Error importing to database: {e}")
        raise


