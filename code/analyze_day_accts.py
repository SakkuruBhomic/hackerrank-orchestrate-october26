import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from main import AuditAgent, load_csv, DATASET
import json

agent = AuditAgent()
sample_reqs = list(load_csv(DATASET / 'sample_deletion_requests.csv'))
sample_out = {r['case_id']: r for r in load_csv(DATASET / 'sample_output.csv')}

# For each sample request, see which accounts are expected and how they relate to the worker submissions
for req in sample_reqs:
    cid = req["case_id"]
    exp_steps = json.loads(sample_out[cid]["steps_json"])
    exp_acct = [s["resource_id"] for s in exp_steps if s["system_id"] == "account_service"]
    exp_downstream = [s["resource_id"] for s in exp_steps if s["system_id"] != "account_service"]
    
    # Check worker submissions on that day
    rep_d = req["reported_at"][:10]
    day_accts = []
    for act in agent.worker_acts:
        if act["target_system"] == "account_service" and ("submitted" in act["details"] or "submit" in act["details"]):
            if act["event_time"][:10] == rep_d and act["resource_id"] not in day_accts:
                day_accts.append(act["resource_id"])
                
    print(f"{cid} ({rep_d}) -> exp acct: {exp_acct}")
    print(f"   day accts ({len(day_accts)}): {day_accts}")
    print(f"   exp downstream: {exp_downstream}")
