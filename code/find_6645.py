from pathlib import Path

target = "6645"
for p in Path('.').rglob('*'):
    if p.is_file() and not p.name.endswith('.pyc') and not 'git' in str(p):
        try:
            b = p.read_bytes()
            if target.encode('utf-8') in b:
                print("FOUND 6645 in", p)
        except Exception:
            pass
