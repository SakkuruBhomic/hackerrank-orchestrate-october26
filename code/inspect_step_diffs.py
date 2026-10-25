import csv
import json
import sys
sys.path.insert(0, 'code')
from main import AuditAgent, load_csv, DATASET

agent = AuditAgent()
sample_reqs = load_csv(DATASET / "sample_deletion_requests.csv")
sample_out = {r["case_id"]: r for r in load_csv(DATASET / "sample_output.csv")}

for req in sample_reqs:
    cid = req["case_id"]
    exp_steps = json.loads(sample_out[cid]["steps_json"])
    _, _, act_steps_str = agent.process_case(req)
    act_steps = json.loads(act_steps_str)

    if act_steps != exp_steps:
        print(f"\n=== {cid} ===")
        print(f"Exp ({len(exp_steps)}):")
        for s in exp_steps:
            print(f"  {s['phase']:12} {s['system_id']:18} {s['resource_id']:18} {s['operation']:25} {s['state']:10} {s['evidence_id']}")
        print(f"Got ({len(act_steps)}):")
        for s in act_steps:
            print(f"  {s['phase']:12} {s['system_id']:18} {s['resource_id']:18} {s['operation']:25} {s['state']:10} {s['evidence_id']}")
