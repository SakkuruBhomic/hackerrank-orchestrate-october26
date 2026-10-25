import csv
import json
import sys
sys.path.insert(0, 'code')
from main import AuditAgent, load_csv, DATASET

agent = AuditAgent()
sample_reqs = {r['case_id']: r for r in load_csv(DATASET / "sample_deletion_requests.csv")}
sample_out = {r['case_id']: r for r in load_csv(DATASET / "sample_output.csv")}

failing = ['case_06', 'case_09', 'case_10', 'case_12', 'case_16', 'case_18', 'case_20', 'case_22', 'case_26']

for cid in failing:
    req = sample_reqs[cid]
    exp = sample_out[cid]
    exp_steps = json.loads(exp['steps_json'])
    actual_cid, act_status, act_steps_str = agent.process_case(req)
    act_steps = json.loads(act_steps_str)
    
    print(f"\n================ {cid} ================")
    print(f"Email: {req.get('email')} | Reported at: {req.get('reported_at')} | Audit at: {req.get('audit_at')}")
    print(f"Expected Status: {exp['deletion_status']} | Got Status: {act_status}")
    print("--- Expected Steps ---")
    for s in exp_steps:
        print(f"  {s['phase']} {s['system_id']} {s['resource_id']} {s['operation']} {s['state']} (ev: {s['evidence_id']})")
    print("--- Actual Steps ---")
    for s in act_steps:
        print(f"  {s['phase']} {s['system_id']} {s['resource_id']} {s['operation']} {s['state']} (ev: {s['evidence_id']})")
