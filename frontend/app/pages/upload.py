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

logger = logging.getLogger(__name__)

upload_pages = Blueprint("upload", __name__)

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "../../../temp_uploads")
ALLOWED_RECEIPT_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}
ALLOWED_CSV_EXTENSIONS = {'csv'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@upload_pages.route("/upload")
def upload():
    """Main upload page - requires authentication"""
    if "user_email" not in session:
        flash("Please login to access the upload", "error")
        return redirect(url_for("login.login"))
    
    # Get receipt count from session
    receipt_count = len(session.get("uploaded_receipts", []))
    
    return render_template(
        "upload.html", 
        user_email=session.get("user_email"),
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
    """Handle CSV upload and immediately process with ML predictions"""
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
        # Save CSV temporarily
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        # Read and validate CSV
        df = pd.read_csv(filepath)
        
        # Store CSV data for preview
        csv_preview = {
            "columns": df.columns.tolist(),
            "preview": df.head(10).values.tolist(),
            "row_count": len(df),
            "filename": filename
        }
        
        # Process with ML prediction
        prediction_results = process_csv_prediction(filepath, df)
        
        # Save processed CSV to data directory
        processed_dir = os.path.join(os.path.dirname(__file__), "../../../data/processed_csv")
        os.makedirs(processed_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        user_email = session.get("user_email", "unknown").replace("@", "_at_")
        processed_file = os.path.join(processed_dir, f"csv_{user_email}_{timestamp}.csv")
        df.to_csv(processed_file, index=False)
        
        # Clean up temp file
        os.remove(filepath)
        
        flash(f"CSV uploaded successfully! Processed {len(df)} rows", "success")
        
        return render_template(
            "upload.html",
            user_email=session.get("user_email"),
            receipt_count=len(session.get("uploaded_receipts", [])),
            csv_data=csv_preview,
            prediction_results=prediction_results
        )
        
    except Exception as e:
        flash(f"Error processing CSV: {str(e)}", "error")
        return redirect(url_for("upload.upload"))

def process_csv_prediction(csv_path, df):
    """Process CSV data using ML prediction system"""
    try:
        # Import ML prediction functions
        ml_dir = os.path.join(os.path.dirname(__file__), "../../../ml")
        sys.path.insert(0, ml_dir)
        sys.path.insert(0, os.path.join(ml_dir, "src"))
        
        from src.predict import predict_next_horizon, create_lookback_window
        from src.config import Config
        from src.cleaner import DataCleaner
        from src.feature_engineer import FeatureEngineer
        import tensorflow as tf
        import numpy as np
        
        cfg = Config()
        
        # Load the trained model
        model_path = os.path.join(ml_dir, "models/demand_lstm/best.keras")
        if not os.path.exists(model_path):
            return {"error": "Model not found"}
        
        model = tf.keras.models.load_model(model_path)
        
        # Determine product_id
        if "product_id" in df.columns:
            product_id = df["product_id"].iloc[0]
            # Filter for specific product
            df_product = df[df["product_id"] == product_id].copy()
        else:
            product_id = "Unknown"
            df_product = df.copy()
        
        # Clean the data
        cleaner = DataCleaner()
        df_product = cleaner.clean(df_product)
        
        # Check if we have enough data
        if len(df_product) < cfg.LOOKBACK:
            return {
                "error": f"Not enough data. Need at least {cfg.LOOKBACK} rows, got {len(df_product)}",
                "csv_rows_processed": len(df)
            }
        
        # Aggregate by date if needed
        if "date" in df_product.columns:
            df_product = (
                df_product.groupby("date", as_index=False)
                .agg({
                    "units_sold": "sum" if "units_sold" in df_product.columns else "first",
                    "inventory_level": "sum" if "inventory_level" in df_product.columns else "first",
                    "units_ordered": "sum" if "units_ordered" in df_product.columns else "first",
                    "price": "mean" if "price" in df_product.columns else "first",
                    "discount": "mean" if "discount" in df_product.columns else "first",
                    "holiday_promotion": "max" if "holiday_promotion" in df_product.columns else "first",
                    "seasonality": "first" if "seasonality" in df_product.columns else "first"
                })
            )
        
        # Select required columns (use defaults if missing)
        required_cols = ["date", "units_sold", "inventory_level", "units_ordered", 
                        "price", "discount", "holiday_promotion", "seasonality"]
        for col in required_cols:
            if col not in df_product.columns:
                if col == "date":
                    return {"error": "CSV must contain a 'date' column"}
                elif col == "units_sold":
                    return {"error": "CSV must contain a 'units_sold' column"}
                else:
                    df_product[col] = 0  # Default value
        
        df_product = df_product[required_cols]
        
        # Add features
        fe = FeatureEngineer()
        df_product = fe.add_calendar_features(df_product)
        df_product = fe.add_lag_features(df_product)
        df_product = df_product.dropna().reset_index(drop=True)
        
        # Check again after feature engineering
        if len(df_product) < cfg.LOOKBACK:
            return {
                "error": f"Not enough data after processing. Need at least {cfg.LOOKBACK} rows",
                "csv_rows_processed": len(df)
            }
        
        # Make prediction
        results = predict_next_horizon(model, df_product, cfg)
        
        # Add metadata
        results["product_id"] = product_id
        results["csv_rows_processed"] = len(df)
        results["data_rows_used"] = len(df_product)
        
        return results
        
    except Exception as e:
        print(f"Error in ML prediction: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}
