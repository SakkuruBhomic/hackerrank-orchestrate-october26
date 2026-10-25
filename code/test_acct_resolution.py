import csv
import json
import re
from pathlib import Path
from main import parse_ts, AuditAgent

agent = AuditAgent()
sample_reqs = list(csv.DictReader(open('dataset/sample_deletion_requests.csv', encoding='utf-8')))
sample_out = {r['case_id']: r for r in csv.DictReader(open('dataset/sample_output.csv', encoding='utf-8'))}

# Build mapping of (resource_id -> account_id) from system_activity
# In system_activity, worker processes accounts, then downstream resources
res_to_acct = {}
curr_acct = None
accts_on_day = []

for a in agent.system_activity:
    if a["source_system"] == "deletion_worker":
        if a["target_system"] == "account_service":
            curr_acct = a["resource_id"]
        elif curr_acct:
            res_to_acct[a["resource_id"]] = curr_acct

matches = 0
total = 0
for req in sample_reqs:
    cid = req["case_id"]
    exp_steps = json.loads(sample_out[cid]["steps_json"])
    exp_acct = None
    for s in exp_steps:
        if s["system_id"] == "account_service":
            exp_acct = s["resource_id"]
            break
    if not exp_acct:
        continue
    total += 1
    
    # Try finding acct
    uid = agent.id_index.get(req["email"].strip().lower())
    tokens = agent.ev_manifest # just check
    
    # Check if numbered
    u_num_m = re.search(r"user_(\d+)", uid) if uid else None
    got_acct = None
    if u_num_m and int(u_num_m.group(1)) <= 10:
        got_acct = f"account_{int(u_num_m.group(1)):03d}"
    
    if not got_acct and uid:
        user_tokens = {uid, req["email"].strip().lower()}
        # Check evidence for user's downstream resources
        downstream = []
        for ev in agent.ev.records:
            if ev["id_tokens"] & user_tokens:
                if ev["system_id"] == "account_service":
                    got_acct = ev["resource_id"]
                    break
                downstream.append(ev["resource_id"])
        
        if not got_acct:
            for res in downstream:
                if res in res_to_acct:
                    got_acct = res_to_acct[res]
                    break

    ok = "MATCH" if got_acct == exp_acct else "DIFF"
    if got_acct == exp_acct:
        matches += 1
    print(f"{cid:8} | exp: {exp_acct:15} | got: {str(got_acct):15} | {ok}")

print(f"\nAccount Resolution: {matches}/{total} ({matches/total*100:.1f}%)")
