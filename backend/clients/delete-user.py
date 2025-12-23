import sqlite3
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(SCRIPT_DIR, "clients.db")

def delete_user(value):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Detect if value is numeric (tax code) or email
    if value.isdigit():
        # Delete by identifier
        cursor.execute("DELETE FROM clients WHERE identifier = ?", (value,))
    else:
        # Delete by email
        cursor.execute("DELETE FROM clients WHERE email = ?", (value,))

    conn.commit()
    deleted_count = cursor.rowcount  # number of rows affected
    conn.close()

    if deleted_count > 0:
        print(f"User deleted successfully. Rows affected: {deleted_count}")
        return True
    else:
        print("No user found with this value.")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python delete-user.py <taxcode_or_email>")
        print("It will return 0 if user deleted, 1 if user not found, 2 on error.")
        sys.exit(2)

    value = sys.argv[1]
    try:
        if delete_user(value):
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        print(f"Error deleting user: {e}")
        sys.exit(2)
