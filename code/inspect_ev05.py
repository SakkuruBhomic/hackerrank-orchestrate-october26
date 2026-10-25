import sqlite3
import json

conn = sqlite3.connect(':memory:')
conn.executescript(open('dataset/evidence/databases/customer_data_read_replica_20260921.sql', encoding='utf-8').read())
cur = conn.cursor()
for table in ['customer_data_primary', 'customer_data_read_replica']:
    cur.execute(f"SELECT * FROM {table} WHERE resource_id in ('search_1007', 'search_8911', 'account_994')")
    rows = cur.fetchall()
    print(table, len(rows))
    for r in rows:
        print(" ", r[0], r[1], r[2], r[3])
