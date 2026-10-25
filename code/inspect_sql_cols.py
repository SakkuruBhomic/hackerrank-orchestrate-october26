import sqlite3
from pathlib import Path

for p in sorted(Path('dataset/evidence/databases').glob('*.sql')):
    conn = sqlite3.connect(':memory:')
    try:
        conn.executescript(p.read_text(encoding='utf-8', errors='ignore'))
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        for t in tables:
            cur.execute(f'SELECT * FROM "{t}" LIMIT 1')
            cols = [d[0] for d in cur.description]
            row = cur.fetchone()
            print(f"{p.name:45} | {t:32} | cols: {cols}")
    except Exception as e:
        print(f"Error on {p.name}: {e}")
    finally:
        conn.close()
