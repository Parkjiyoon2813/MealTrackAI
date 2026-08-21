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
    connection.commit()

    try:
        cursor.execute(
            "ALTER TABLE meals ADD COLUMN outside_dinner INTEGER DEFAULT 0"
        )
        connection.commit()
    except sqlite3.OperationalError:
        pass

    return connection, cursor
