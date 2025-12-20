import requests
import json

def init_postgres():
    url = "http://localhost:8000/query"
    sql = "CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, name TEXT, role TEXT)"
    try:
        res = requests.post(url, json={"sql": sql})
        print(f"Postgres Init: {res.status_code} - {res.text}")
        
        # Insert Data
        sql_insert = "INSERT INTO users (name, role) VALUES ('Alice', 'Engineer'), ('Bob', 'Manager')"
        res = requests.post(url, json={"sql": sql_insert})
        print(f"Postgres Insert: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    init_postgres()
