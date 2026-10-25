import json
from pathlib import Path

target_accounts = {
    'account_5482', 'account_7012', 'account_8858', 'account_4857', 'account_5521',
    'account_5037', 'account_3610', 'account_5684', 'account_3960', 'account_4163', 'account_4990'
}

for p in Path('dataset/evidence').rglob('*.*'):
    try:
        txt = p.read_text(encoding='utf-8', errors='ignore')
        for acct in target_accounts:
            if acct in txt:
                print(f"{acct:15} in {p.name}")
    except:
        pass
