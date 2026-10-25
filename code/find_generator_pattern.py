import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from main import AuditAgent, load_csv, DATASET
import json
from collections import defaultdict

agent = AuditAgent()
sample_reqs = list(load_csv(DATASET / 'sample_deletion_requests.csv'))
sample_out = {r['case_id']: r for r in load_csv(DATASET / 'sample_output.csv')}

# Map from downstream resource to its expected account
downstream_to_acct = {}
for req in sample_reqs:
    cid = req["case_id"]
    exp_steps = json.loads(sample_out[cid]["steps_json"])
    exp_acct = None
    for s in exp_steps:
        if s["system_id"] == "account_service":
            exp_acct = s["resource_id"]
            break
    if exp_acct:
        for s in exp_steps:
            if s["system_id"] != "account_service" and s["system_id"] != "security_service":
                downstream_to_acct[s["resource_id"]] = (exp_acct, cid)

# Check system activity events for each downstream resource
for res, (acct, cid) in sorted(downstream_to_acct.items()):
    acts = [a for a in agent.system_activity if a["resource_id"] == res]
    if acts:
        act = acts[0]
        print(f"{res:15} -> exp {acct:12} ({cid:7}) | act_time: {act['event_time']} | details: {act['details'][:50]}")
    else:
        print(f"{res:15} -> exp {acct:12} ({cid:7}) | NO ACT")
