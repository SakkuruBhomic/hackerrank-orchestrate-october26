import csv
import json
import sys
sys.stdout.reconfigure(encoding="utf-8")

sample_reqs = {r['case_id']: r for r in csv.DictReader(open('dataset/sample_deletion_requests.csv', encoding='utf-8'))}
sample_out = {r['case_id']: r for r in csv.DictReader(open('dataset/sample_output.csv', encoding='utf-8'))}

print("Fieldnames:", list(sample_reqs[list(sample_reqs.keys())[0]].keys()))

for cid in ['case_06', 'case_09', 'case_10', 'case_12', 'case_16', 'case_18', 'case_20', 'case_22', 'case_26']:
    req = sample_reqs[cid]
    out = sample_out[cid]
    steps = json.loads(out['steps_json'])
    uid = req.get('requester_id') or req.get('user_id') or req.get('subject_id')
    print(f"\n=== {cid} (user: {uid}) exp: {out['deletion_status']} ===")
    print("Request:", req['request_text'])
    print("Reported at:", req['reported_at'], "Audit at:", req['audit_at'])
    print("Expected steps:")
    for s in steps:
        print(f"   {s['phase']} | {s['system_id']} | {s['resource_id']} | {s['operation']} | {s['state']} | ev: {s['evidence_id']}")
