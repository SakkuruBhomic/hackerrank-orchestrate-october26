from pathlib import Path
import re

all_tables = set()
for p in Path('dataset/evidence/databases').glob('*.sql'):
    with open(p, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            m = re.search(r'CREATE TABLE (?:IF NOT EXISTS )?["\']?(\w+)["\']?', line, re.IGNORECASE)
            if m:
                all_tables.add(m.group(1))

print("All tables across all SQL files:")
for t in sorted(all_tables):
    print(" ", t)
