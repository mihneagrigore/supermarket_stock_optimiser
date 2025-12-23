import sqlite3
import json
import uuid
import argparse
import sys
from datetime import datetime

OPTIONAL_FIELDS = [
    "Category",
    "Supplier_ID",
    "Supplier_Name",
    "Stock_Quantity",
    "Reorder_Level",
    "Reorder_Quantity",
    "Expiration_Date",
    "Warehouse_Location",
    "Sales_Volume",
    "Inventory_Turnover_Rate",
    "Status"
]


def ask(field, default=None):
    prompt = f"{field}"
    if default not in (None, ""):
        prompt += f" [{default}]"
    prompt += ": "
    value = input(prompt).strip()
    return default if value == "" else value


def load_json(json_file):
    with open(json_file, "r", encoding="utf-8") as f:
        return json.load(f)


def find_product(cursor, name, price):
    cursor.execute("""
        SELECT * FROM inventory
        WHERE Product_Name = ? AND Unit_Price = ?
    """, (name, price))
    return cursor.fetchone()


def insert_product(cursor, data):
    fields = ", ".join(data.keys())
    placeholders = ", ".join("?" for _ in data)
    cursor.execute(
        f"INSERT INTO inventory ({fields}) VALUES ({placeholders})",
        list(data.values())
    )


def update_product(cursor, row_id, updates):
    if not updates:
        return
    assignments = ", ".join(f"{k} = ?" for k in updates)
    cursor.execute(
        f"UPDATE inventory SET {assignments} WHERE id = ?",
        list(updates.values()) + [row_id]
    )


def main():
    if len(sys.argv) != 3:
        print("Error: Missing required arguments", file=sys.stderr)
        print("Usage: python json-import.py <database_file> <json_file>", file=sys.stderr)
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Import JSON receipt data into SQLite inventory database")
    parser.add_argument("database", help="Path to the SQLite database file")
    parser.add_argument("json_file", help="Path to the JSON receipt file")
    args = parser.parse_args()

    receipt = load_json(args.json_file)
    conn = sqlite3.connect(args.database)
    cursor = conn.cursor()

    # Create table if it doesn't exist
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
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
    )
    """)
    conn.commit()

    for item in receipt["products"]:
        name = item["productName"].strip()
        price = float(item["productPrice"])

        print(f"\n{name} | {price:.2f}")

        existing = find_product(cursor, name, price)

        if existing:
            print("Product found in database.")
            choice = input("Keep existing records? (y/n): ").lower()

            if choice == "n":
                col_names = [d[0] for d in cursor.description]
                current = dict(zip(col_names, existing))

                updates = {}
                for field in OPTIONAL_FIELDS:
                    updates[field] = ask(field, current.get(field))

                updates["Last_Order_Date"] = datetime.now().date().isoformat()
                update_product(cursor, current["id"], updates)

        else:
            print("New product. Please enter details:")

            new_data = {
                "Product_ID": str(uuid.uuid4()),
                "Product_Name": name,
                "Unit_Price": price,
                "Date_Received": datetime.now().date().isoformat()
            }

            # Optional: store unit info in Category or Status if you want
            if "unit" in item:
                new_data["Category"] = item["unit"]

            for field in OPTIONAL_FIELDS:
                if field not in new_data:
                    new_data[field] = ask(field)

            insert_product(cursor, new_data)

    conn.commit()
    conn.close()
    print("\n Receipt JSON successfully synced with inventory.")


if __name__ == "__main__":
    main()
