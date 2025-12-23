import sqlite3
import csv
import os
import sys
from datetime import datetime

DB_FILE = "products.db"
CSV_FILE = "products.csv"
LOG_FILE = "import_errors.log"

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

# Drop table to avoid conflicts
cursor.execute("DROP TABLE IF EXISTS inventory")

# Create table with Product_ID as TEXT
cursor.execute("""
CREATE TABLE inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    Product_ID TEXT,
    Product_Name TEXT NOT NULL,
    Category TEXT,
    Supplier_ID INTEGER,
    Supplier_Name TEXT,
    Stock_Quantity INTEGER,
    Reorder_Level INTEGER,
    Reorder_Quantity INTEGER,
    Unit_Price REAL,
    Date_Received DATE,
    Last_Order_Date DATE,
    Expiration_Date DATE,
    Warehouse_Location TEXT,
    Sales_Volume INTEGER,
    Inventory_Turnover_Rate REAL,
    Status TEXT
);
""")
conn.commit()

# Import data from CSV
insert_sql = """
INSERT INTO inventory (
    Product_ID, Product_Name, Category, Supplier_ID, Supplier_Name,
    Stock_Quantity, Reorder_Level, Reorder_Quantity, Unit_Price,
    Date_Received, Last_Order_Date, Expiration_Date,
    Warehouse_Location, Sales_Volume, Inventory_Turnover_Rate, Status
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
                # Fix Product_ID, Supplier_ID, and Unit_Price
                product_id = row["Product_ID"].strip()
                supplier_id = row["Supplier_ID"].strip()             # <-- define this
                unit_price = parse_float(row["Unit_Price"].replace("$", "").strip())

                rows_to_insert.append((
                    product_id,                          # Product_ID (TEXT)
                    row["Product_Name"].strip(),         # Product_Name
                    row["Category"].strip(),             # Category
                    supplier_id,                         # Supplier_ID (TEXT)
                    row["Supplier_Name"].strip(),        # Supplier_Name
                    parse_int(row["Stock_Quantity"]),    # Stock_Quantity
                    parse_int(row["Reorder_Level"]),     # Reorder_Level
                    parse_int(row["Reorder_Quantity"]),  # Reorder_Quantity
                    unit_price,                          # Unit_Price
                    parse_date(row["Date_Received"]),    # Date_Received
                    parse_date(row["Last_Order_Date"]),  # Last_Order_Date
                    parse_date(row["Expiration_Date"]),  # Expiration_Date
                    row["Warehouse_Location"].strip(),   # Warehouse_Location
                    parse_int(row["Sales_Volume"]),      # Sales_Volume
                    parse_float(row["Inventory_Turnover_Rate"]), # Inventory_Turnover_Rate
                    row["Status"].strip()                # Status
                ))
                row_count += 1
            except Exception as e:
                error_count += 1
                log.write(f"Line {line_num}: {e} | Data: {row}\n")


# Bulk insert
cursor.executemany(insert_sql, rows_to_insert)
conn.commit()

# Sort by Product_Name case-insensitively

cursor.execute("""
CREATE TABLE inventory_sorted AS
SELECT *
FROM inventory
ORDER BY Product_Name COLLATE NOCASE ASC;
""")

cursor.execute("DROP TABLE inventory")

cursor.execute("""
CREATE TABLE inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    Product_ID TEXT,
    Product_Name TEXT NOT NULL,
    Category TEXT,
    Supplier_ID INTEGER,
    Supplier_Name TEXT,
    Stock_Quantity INTEGER,
    Reorder_Level INTEGER,
    Reorder_Quantity INTEGER,
    Unit_Price REAL,
    Date_Received DATE,
    Last_Order_Date DATE,
    Expiration_Date DATE,
    Warehouse_Location TEXT,
    Sales_Volume INTEGER,
    Inventory_Turnover_Rate REAL,
    Status TEXT
);
""")

cursor.execute("""
INSERT INTO inventory (
    Product_ID, Product_Name, Category, Supplier_ID, Supplier_Name,
    Stock_Quantity, Reorder_Level, Reorder_Quantity, Unit_Price,
    Date_Received, Last_Order_Date, Expiration_Date,
    Warehouse_Location, Sales_Volume, Inventory_Turnover_Rate, Status
)
SELECT
    Product_ID, Product_Name, Category, Supplier_ID, Supplier_Name,
    Stock_Quantity, Reorder_Level, Reorder_Quantity, Unit_Price,
    Date_Received, Last_Order_Date, Expiration_Date,
    Warehouse_Location, Sales_Volume, Inventory_Turnover_Rate, Status
FROM inventory_sorted;
""")

cursor.execute("DROP TABLE inventory_sorted")

conn.commit()
conn.close()

print(f"Import completed successfully: {row_count} rows imported, {error_count} errors logged.")
sys.exit(0)
