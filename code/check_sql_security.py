import sqlite3
from pathlib import Path

for p in sorted(Path('dataset/evidence/databases').glob('*.sql')):
    txt = p.read_text(encoding='utf-8', errors='ignore')
    if 'security_service' in txt or 'audit_record' in txt:
        print('FILE:', p.name)
        conn = sqlite3.connect(':memory:')
        try:
            conn.executescript(txt)
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            for t in [r[0] for r in cur.fetchall()]:
                cur.execute(f'SELECT * FROM "{t}" LIMIT 1')
                cols = [d[0] for d in cur.description]
                if 'origin_system' in cols:
                    cur.execute(f'SELECT resource_id, record_json FROM "{t}" WHERE origin_system="security_service"')
                    rows = cur.fetchall()
                    if rows:
                        print(f'  Table {t}: {len(rows)} security rows')
                        for r in rows[:3]:
                            print('   ', r[0], r[1][:100])
                elif 'security_audit_records' in t:
                    cur.execute(f'SELECT * FROM "{t}"')
                    rows = cur.fetchall()
                    print(f'  Table {t}: {len(rows)} rows')
                    for r in rows[:3]:
                        print('   ', r)
        except Exception as e:
            print('  error:', e)
