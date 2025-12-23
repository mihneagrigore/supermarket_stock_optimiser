import sqlite3
import os
import sys
import bcrypt

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(SCRIPT_DIR, "clients.db")

def validate_user(email, password):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Fetch the user by email
    cursor.execute("SELECT password FROM clients WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()

    if row:
        hashed_password = row[0]
        # Check password with bcrypt
        if bcrypt.checkpw(password.encode('utf-8'), hashed_password):
            print("Credentials are valid.")
            return True
        else:
            print("Invalid password.")
            return False
    else:
        print("Email not found.")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python validate-user.py <email> <password>")
        print("Exit codes: 0 = valid, 1 = invalid credentials, 2 = error")
        sys.exit(2)

    email = sys.argv[1]
    password = sys.argv[2]

    try:
        if validate_user(email, password):
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        print(f"Error validating user: {e}")
        sys.exit(2)
