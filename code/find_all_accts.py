import glob, os

accts = [
    'account_4745', 'account_994', 'account_4092', 'account_5521', 
    'account_9102', 'account_5037', 'account_4163'
]

for acct in accts:
    print(f"=== {acct} ===")
    for p in glob.glob('dataset/**/*', recursive=True):
        if os.path.isfile(p):
            try:
                with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if acct in content:
                        print("  found in", p)
            except Exception:
                pass
