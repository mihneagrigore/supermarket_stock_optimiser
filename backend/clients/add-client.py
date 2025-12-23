import sqlite3
import json
import sys
import os
import bcrypt

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE = os.path.join(SCRIPT_DIR, "../../data/company-details/company-details.json")
DB_FILE = os.path.join(SCRIPT_DIR, "clients.db")

def create_table():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            identifier TEXT UNIQUE,          -- cif or cui must be unique
            numar_reg_com TEXT,
            denumire TEXT,
            adresa TEXT,
            tva TEXT,                       -- 'yes' if exists, 'no' otherwise
            email TEXT UNIQUE,              -- email must be unique
            password TEXT                   -- hashed password
        )
    ''')
    conn.commit()
    conn.close()

def add_client(email, password):
    # Load client data from JSON
    if not os.path.exists(JSON_FILE):
        print(f"JSON file '{JSON_FILE}' not found.")
        exit(1)

    with open(JSON_FILE, "r", encoding="utf-8") as f:
        client_data = json.load(f)

    # Determine identifier (cif or cui)
    identifier = client_data.get("cif") or client_data.get("cui") or None

    # Handle tva field
    tva = "yes" if client_data.get("tva") else "no"

    # Extract other fields (leave empty if null)
    numar_reg_com = client_data.get("numar_reg_com") or None
    denumire = client_data.get("denumire") or None
    adresa = client_data.get("adresa") or None

    # Hash the password with bcrypt
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    # Insert into DB with duplicate handling
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO clients (identifier, numar_reg_com, denumire, adresa, tva, email, password)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (identifier, numar_reg_com, denumire, adresa, tva, email, hashed_password))
        conn.commit()
        print("Client added successfully!")
    except sqlite3.IntegrityError as e:
        # This catches UNIQUE constraint failures
        print(f"Failed to add client: {e}")
        print("The identifier or email already exists in the database.")
        exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python add-client.py <email> <password>")
        exit(1)

    email = sys.argv[1]
    password = sys.argv[2]

    create_table()  # ensures DB exists
    add_client(email, password)
    exit(0)
