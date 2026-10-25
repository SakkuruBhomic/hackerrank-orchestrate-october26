import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from main import AuditAgent, load_csv, DATASET
import json
from collections import defaultdict

agent = AuditAgent()
sample_reqs = list(load_csv(DATASET / 'sample_deletion_requests.csv'))
sample_out = {r['case_id']: r for r in load_csv(DATASET / 'sample_output.csv')}

# All requests in both sample and full dataset
all_reqs = list(load_csv(DATASET / 'deletion_requests.csv')) + sample_reqs
# Filter out non-deletion requests
all_del_reqs = [r for r in all_reqs if "delete" in r.get("request_text","").lower() or "remove" in r.get("request_text","").lower() or "erase" in r.get("request_text","").lower() or r["case_id"] in [f"case_{i:02d}" for i in range(1, 33)]]

# Group by reported_at date
reqs_by_date = defaultdict(list)
for r in all_reqs:
    d = r["reported_at"][:10]
    reqs_by_date[d].append(r)

# Group worker accounts by date
accts_by_date = defaultdict(list)
for act in agent.worker_acts:
    if act["target_system"] == "account_service" and ("submitted" in act["details"] or "submit" in act["details"]):
        d = act["event_time"][:10]
        if act["resource_id"] not in accts_by_date[d]:
            accts_by_date[d].append(act["resource_id"])

# Test sample requests
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
    
    # Let's see if sorting reqs by requested_at on that day matches accts_by_date
    d = req["reported_at"][:10]
    day_r = reqs_by_date[d]
    # Sort day requests by requested_at, then case_id
    sorted_day_r = sorted(day_r, key=lambda x: (x["requested_at"], x["case_id"]))
    day_a = accts_by_date.get(d, [])
    
    # Try to find req index
    try:
        r_idx = [r["case_id"] for r in sorted_day_r].index(cid)
        pred_acct = day_a[r_idx] if r_idx < len(day_a) else None
    except Exception:
        pred_acct = None
        
    print(f"{cid} | exp: {exp_acct:15} | pred: {str(pred_acct):15} | {'MATCH' if pred_acct == exp_acct else 'DIFF'}")
    if pred_acct == exp_acct:
        matches += 1

print(f"\nOrder by requested_at Accuracy: {matches}/{total} ({matches/total*100:.1f}%)")
