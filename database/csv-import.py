import sqlite3
import csv
import os
import sys
import argparse
from datetime import datetime

DB_FILE = "products.db"
CSV_FILE = "products.csv"
LOG_FILE = "import_errors.log"

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Import CSV data into SQLite inventory database")
parser.add_argument("client_id", type=int, help="Client ID to assign to all imported products")
parser.add_argument("--csv", default=CSV_FILE, help=f"Path to CSV file (default: {CSV_FILE})")
parser.add_argument("--db", default=DB_FILE, help=f"Path to database file (default: {DB_FILE})")
args = parser.parse_args()

CLIENT_ID = args.client_id
CSV_FILE = args.csv
DB_FILE = args.db

# Check if required files exist
if not os.path.exists(CSV_FILE):
    print(f"Error: CSV file '{CSV_FILE}' not found.")
    sys.exit(1)

# Database will be created if it doesn't exist
if not os.path.exists(DB_FILE):
    print(f"Database file '{DB_FILE}' not found. Creating new database...")

def parse_int(value, default=0):
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def parse_float(value, default=0.0):
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def parse_date(value):
    """Accepts YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY"""
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    return None

# Seup database connection
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

# Create table if it doesn't exist (preserves existing data)
cursor.execute("""
CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    Date DATE,
    Store_ID TEXT,
    Product_ID TEXT,
    Category TEXT,
    Region TEXT,
    Inventory_Level INTEGER,
    Units_Sold INTEGER,
    Units_Ordered INTEGER,
    Demand_Forecast REAL,
    Price REAL,
    Discount REAL,
    Weather_Condition TEXT,
    Holiday_Promotion INTEGER,
    Competitor_Pricing REAL,
    Seasonality TEXT,
    FOREIGN KEY (client_id) REFERENCES clients(id),
    UNIQUE(client_id, Date, Store_ID, Product_ID)
);
""")
conn.commit()

# Import data from CSV
insert_sql = """
INSERT INTO inventory (
    client_id, Date, Store_ID, Product_ID, Category, Region,
    Inventory_Level, Units_Sold, Units_Ordered, Demand_Forecast,
    Price, Discount, Weather_Condition, Holiday_Promotion,
    Competitor_Pricing, Seasonality
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

rows_to_insert = []
row_count = 0
error_count = 0

with open(LOG_FILE, "w", encoding="utf-8") as log:
    with open(CSV_FILE, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for line_num, row in enumerate(reader, start=2):
            try:
                # Parse values with appropriate types
                date = parse_date(row["Date"].strip())
                store_id = row["Store ID"].strip()
                product_id = row["Product ID"].strip()
                category = row["Category"].strip()
                region = row["Region"].strip()
                inventory_level = parse_int(row["Inventory Level"])
                units_sold = parse_int(row["Units Sold"])
                units_ordered = parse_int(row["Units Ordered"])
                demand_forecast = parse_float(row["Demand Forecast"])
                price = parse_float(row["Price"])
                discount = parse_float(row["Discount"])
                weather_condition = row["Weather Condition"].strip()
                holiday_promotion = parse_int(row["Holiday/Promotion"])
                competitor_pricing = parse_float(row["Competitor Pricing"])
                seasonality = row["Seasonality"].strip()

                rows_to_insert.append((
                    CLIENT_ID,                     # client_id
                    date,                          # Date
                    store_id,                      # Store_ID
                    product_id,                    # Product_ID
                    category,                      # Category
                    region,                        # Region
                    inventory_level,               # Inventory_Level
                    units_sold,                    # Units_Sold
                    units_ordered,                 # Units_Ordered
                    demand_forecast,               # Demand_Forecast
                    price,                         # Price
                    discount,                      # Discount
                    weather_condition,             # Weather_Condition
                    holiday_promotion,             # Holiday_Promotion
                    competitor_pricing,            # Competitor_Pricing
                    seasonality                    # Seasonality
                ))
                row_count += 1
            except Exception as e:
                error_count += 1
                log.write(f"Line {line_num}: {e} | Data: {row}\n")


# Bulk insert
cursor.executemany(insert_sql, rows_to_insert)
conn.commit()

print(f"Import completed successfully!")
print(f"Client ID: {CLIENT_ID}")
print(f"Total rows imported: {row_count}")
print(f"Errors encountered: {error_count}")
if error_count > 0:
    print(f"See '{LOG_FILE}' for error details.")

conn.close()
