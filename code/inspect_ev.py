import sqlite3

with open('dataset/evidence/databases/customer_accounts_failover_replica_20260902.sql', encoding='utf-8') as f:
    sql = f.read()

conn = sqlite3.connect(':memory:')
conn.executescript(sql)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()
print('Tables:', tables)
for t, in tables:
    print(f"=== {t} ===")
    cur.execute(f"SELECT * FROM {t}")
    for row in cur.fetchall():
        print(row)
