
import trino
from trino.dbapi import connect
import subprocess
import sys

def create_schema():
    print("Creating Trino schema 'iceberg.public'...")
    try:
        conn = connect(
            host="localhost",
            port=8080,
            user="admin",
            catalog="iceberg",
        )
        cur = conn.cursor()
        cur.execute("CREATE SCHEMA IF NOT EXISTS iceberg.public")
        print("✅ Schema 'iceberg.public' created.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Failed to create schema: {e}")

if __name__ == "__main__":
    create_schema()
