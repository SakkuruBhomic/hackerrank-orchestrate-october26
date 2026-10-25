import json
from pathlib import Path

target_accounts = {
    'account_5482', 'account_7012', 'account_8858', 'account_4857', 'account_3677',
    'account_5521', 'account_5037', 'account_3610', 'account_5684', 'account_3960',
    'account_4163', 'account_9797', 'account_8926', 'account_994', 'account_4990'
}

for p in Path('dataset/evidence').rglob('*.*'):
    if p.suffix in ('.json', '.sql', '.txt'):
        try:
            txt = p.read_text(encoding='utf-8', errors='ignore')
            for acct in target_accounts:
                if acct in txt:
                    # Find matching line or substring
                    for line in txt.splitlines():
                        if acct in line and any(u in line for u in ['user_', '@', 'customer_reference', 'full_name']):
                            print(f"{acct:15} in {p.name:45}: {line[:120]}")
        except:
            pass
