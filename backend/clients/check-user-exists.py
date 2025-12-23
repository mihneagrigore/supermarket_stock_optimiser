import sqlite3
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(SCRIPT_DIR, "clients.db")

def check_user(value):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Try to detect if value is numeric (tax code) or email (contains @)
    if value.isdigit():
        # Check by identifier
        cursor.execute("SELECT * FROM clients WHERE identifier = ?", (value,))
    else:
        # Check by email
        cursor.execute("SELECT * FROM clients WHERE email = ?", (value,))

    result = cursor.fetchone()
    conn.close()

    if result:
        print(f"User found in database: {result}")
        return True
    else:
        print("No user found with this value.")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python check-user-exists.py <taxcode_or_email>")
        print("It will return 0 if user exists, 1 otherwise, 2 on error.")
        sys.exit(2)

    value = sys.argv[1]
    if check_user(value):
        sys.exit(0)
    else:
        sys.exit(1)
