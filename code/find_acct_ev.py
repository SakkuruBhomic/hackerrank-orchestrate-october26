import glob, os

accts = ['account_3866', 'account_5482', 'account_7012', 'account_006']

for acct in accts:
    print(f"=== {acct} ===")
    for p in glob.glob('dataset/**/*', recursive=True):
        if os.path.isfile(p) and not p.endswith('.csv'):
            try:
                with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if acct in content:
                        print("  found in", p)
            except Exception:
                pass
