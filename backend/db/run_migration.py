"""
run_migration.py
-----------------
Runs a .sql migration file against DATABASE_URL using psycopg2 directly --
a psql-free alternative for Windows/Git Bash environments where the
Postgres client tools aren't installed.

Usage:
    python db/run_migration.py db/migrations/002_add_attribution_and_citizens.sql
"""

import os
import sys

import psycopg2

def main():
    if len(sys.argv) != 2:
        print("Usage: python db/run_migration.py <path_to_sql_file>")
        sys.exit(1)

    sql_path = sys.argv[1]
    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        print("ERROR: DATABASE_URL is not set. Run `export $(cat .env | xargs)` first "
              "(or on Windows: set it directly, see note below).")
        sys.exit(1)

    if not os.path.exists(sql_path):
        print(f"ERROR: file not found: {sql_path}")
        sys.exit(1)

    with open(sql_path, "r", encoding="utf-8") as f:
        sql = f.read()

    print(f"Connecting to Neon...")
    conn = psycopg2.connect(database_url)
    conn.autocommit = True  # so CREATE EXTENSION / DDL statements don't need explicit commit
    try:
        with conn.cursor() as cur:
            print(f"Running {sql_path} ...")
            cur.execute(sql)
        print("Migration applied successfully.")
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
