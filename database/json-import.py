import sqlite3
import json
import argparse
import sys
import re
from datetime import datetime
from collections import defaultdict


def load_json(json_file):
    with open(json_file, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_quantity(product_name):
    # Match patterns like "2.000 BUC X" or "3.000 BUC ×" at the start
    match = re.match(r'(\d+(?:\.\d+)?)\s*BUC\s*[X×]\s*(.+)', product_name, re.IGNORECASE)
    if match:
        quantity = float(match.group(1))
        clean_name = match.group(2).strip()
        return quantity, clean_name
    return 1.0, product_name


def normalize_product_name(name):
    # Remove quantity prefix if present
    _, clean_name = extract_quantity(name)
    # Convert to lowercase and remove extra whitespace
    return ' '.join(clean_name.lower().split())


def aggregate_products(products):
    aggregated = defaultdict(lambda: {'quantity': 0, 'total_price': 0, 'original_name': ''})

    for product in products:
        name = product.get("productName", "").strip()
        price = float(product.get("productPrice", 0))

        if not name:  # Skip empty product names
            continue

        quantity, clean_name = extract_quantity(name)
        normalized = normalize_product_name(name)

        aggregated[normalized]['quantity'] += quantity
        aggregated[normalized]['total_price'] += price
        if not aggregated[normalized]['original_name']:
            aggregated[normalized]['original_name'] = clean_name

    return aggregated


def parse_date(date_str):
    if not date_str:
        return datetime.now().date().isoformat()

    try:
        # Try parsing "2023-07-20 00:00:00" format
        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        return dt.date().isoformat()
    except ValueError:
        try:
            # Try parsing "2023-07-20" format
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return dt.date().isoformat()
        except ValueError:
            return datetime.now().date().isoformat()


def get_next_product_id(cursor):
    # Get all existing Product IDs that match the pattern P followed by numbers
    cursor.execute("""
        SELECT DISTINCT Product_ID FROM inventory
        WHERE Product_ID LIKE 'P%'
        ORDER BY Product_ID
    """)

    existing_ids = [row[0] for row in cursor.fetchall()]

    # Extract numeric parts and find the first gap
    used_numbers = set()
    for pid in existing_ids:
        match = re.match(r'P(\d+)', pid)
        if match:
            used_numbers.add(int(match.group(1)))

    # Find first available number starting from 1
    next_num = 1
    while next_num in used_numbers:
        next_num += 1

    return f"P{next_num:04d}"


def main():
    parser = argparse.ArgumentParser(description="Import JSON receipt data into SQLite inventory database")
    parser.add_argument("client_id", type=int, help="Client ID to assign to all imported products")
    parser.add_argument("database", help="Path to the SQLite database file")
    parser.add_argument("json_file", help="Path to the JSON receipt file")
    args = parser.parse_args()

    client_id = args.client_id

    receipts = load_json(args.json_file)
    conn = sqlite3.connect(args.database)
    cursor = conn.cursor()

    # Create table if it doesn't exist
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
    )
    """)
    conn.commit()

    total_inserted = 0
    total_skipped = 0

    # Process each receipt in the JSON array
    for receipt in receipts:
        supermarket = receipt.get("supermarket", "UNKNOWN")
        date = parse_date(receipt.get("date", ""))
        products = receipt.get("products", [])

        print(f"\nProcessing receipt: {supermarket} - {date}")

        # Aggregate duplicate products
        aggregated_products = aggregate_products(products)

        print(f"  Original products: {len(products)}, After aggregation: {len(aggregated_products)}")

        # Insert each aggregated product
        for normalized_name, product_data in aggregated_products.items():
            product_name = product_data['original_name']
            quantity = product_data['quantity']
            total_price = product_data['total_price']
            unit_price = total_price / quantity if quantity > 0 else 0

            # Generate or find Product ID
            product_id = get_next_product_id(cursor)

            # Check if this product already exists (by name and store and date)
            cursor.execute("""
                SELECT id, Units_Sold FROM inventory
                WHERE client_id = ? AND Store_ID = ? AND Product_ID = ? AND Date = ?
            """, (client_id, supermarket, product_id, date))

            existing = cursor.fetchone()

            if existing:
                # Update existing record by adding to quantity
                new_quantity = (existing[1] or 0) + quantity
                cursor.execute("""
                    UPDATE inventory
                    SET Units_Sold = ?, Price = ?
                    WHERE id = ?
                """, (new_quantity, unit_price, existing[0]))
                total_skipped += 1
                print(f"    Updated: {product_name} (Qty: {quantity} → Total: {new_quantity})")
            else:
                # Insert new record
                insert_data = {
                    "client_id": client_id,
                    "Date": date,
                    "Store_ID": supermarket,
                    "Product_ID": product_id,
                    "Category": "",
                    "Region": "",
                    "Inventory_Level": 0,
                    "Units_Sold": int(quantity),
                    "Units_Ordered": 0,
                    "Demand_Forecast": 0.0,
                    "Price": unit_price,
                    "Discount": 0.0,
                    "Weather_Condition": "",
                    "Holiday_Promotion": 0,
                    "Competitor_Pricing": 0.0,
                    "Seasonality": ""
                }

                fields = ", ".join(insert_data.keys())
                placeholders = ", ".join("?" for _ in insert_data)
                cursor.execute(
                    f"INSERT INTO inventory ({fields}) VALUES ({placeholders})",
                    list(insert_data.values())
                )
                total_inserted += 1
                print(f"    Inserted: {product_name} (Qty: {quantity}, Price: {unit_price:.2f})")

    conn.commit()
    conn.close()

    print(f"\n{'='*60}")
    print(f"Import completed successfully!")
    print(f"Client ID: {client_id}")
    print(f"Products inserted: {total_inserted}")
    print(f"Products updated: {total_skipped}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
