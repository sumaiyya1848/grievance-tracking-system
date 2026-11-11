import getpass
import sqlite3

from werkzeug.security import generate_password_hash

from database import get_connection, init_db


def main():
    init_db()
    username = input("New username: ").strip()
    role = input("Role (admin or user): ").strip().lower()
    password = getpass.getpass("Password (at least 8 characters): ")
    again = getpass.getpass("Password again: ")

    if not username:
        print("Username cannot be empty.")
        return
    if role not in ("admin", "user"):
        print("Role must be admin or user.")
        return
    if len(password) < 8:
        print("Password must be at least 8 characters.")
        return
    if password != again:
        print("The two passwords do not match.")
        return

    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, generate_password_hash(password), role),
        )
        conn.commit()
        print(f"User created as {role}.")
    except sqlite3.IntegrityError:
        print("That username already exists.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()