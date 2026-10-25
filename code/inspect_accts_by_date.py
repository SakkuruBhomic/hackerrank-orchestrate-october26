import csv
import json
from collections import defaultdict
from main import parse_ts, AuditAgent

agent = AuditAgent()
sample_reqs = list(csv.DictReader(open('dataset/sample_deletion_requests.csv', encoding='utf-8')))
sample_out = {r['case_id']: r for r in csv.DictReader(open('dataset/sample_output.csv', encoding='utf-8'))}

# Group requests by reported_date
reqs_by_date = defaultdict(list)
for r in sample_reqs:
    d = r['reported_at'][:10]
    reqs_by_date[d].append(r)

# Group worker account submissions by date
accts_by_date = defaultdict(list)
for a in agent.system_activity:
    if a["source_system"] == "deletion_worker" and a["target_system"] == "account_service":
        d = a["event_time"][:10]
        # Only take submissions (not completion reports)
        if "submitted" in a["details"] or "submit" in a["details"]:
            if a["resource_id"] not in accts_by_date[d]:
                accts_by_date[d].append(a["resource_id"])

for d, reqs in sorted(reqs_by_date.items()):
    accts = accts_by_date.get(d, [])
    print(f"\nDate {d}: {len(reqs)} reqs, {len(accts)} worker accounts")
    for r in reqs:
        cid = r["case_id"]
        exp_steps = json.loads(sample_out[cid]["steps_json"])
        exp_acct = [s["resource_id"] for s in exp_steps if s["system_id"] == "account_service"]
        print(f"  {cid:8} (req: {r['requested_at']}) -> exp acct: {exp_acct}")
    print(f"  Worker accounts on {d}: {accts}")
