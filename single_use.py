import sqlite3

def delete_users_table():
    conn = sqlite3.connect('./SQLite/nba.db')
    cursor = conn.cursor()

    try:
        cursor.execute("DROP TABLE IF EXISTS users;")
        conn.commit()
        print("Table 'users' deleted successfully.")
    finally:
        conn.close()

if __name__ == "__main__":
    delete_users_table()