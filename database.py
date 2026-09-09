import sqlite3


def init_database(db_path="meals.db"):
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS meals(
            date TEXT PRIMARY KEY,
            breakfast INTEGER,
            lunch INTEGER,
            dinner INTEGER,
            outside_dinner INTEGER DEFAULT 0,
            bill INTEGER
        )
        """
    )
    # Settings table for user preferences and notification configurations
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS settings(
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )
    connection.commit()

    return connection, cursor


def get_setting(cursor, key, default=None):
    cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = cursor.fetchone()
    if row is not None and row[0] is not None:
        return row[0]
    return default


def set_setting(cursor, connection, key, value):
    cursor.execute(
        """
        INSERT INTO settings (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """,
        (key, str(value)),
    )
    connection.commit()


def get_all_settings(cursor):
    cursor.execute("SELECT key, value FROM settings")
    rows = cursor.fetchall()
    return {r[0]: r[1] for r in rows}

