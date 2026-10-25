import csv, json

sample_reqs = {r['case_id']: r for r in csv.DictReader(open('dataset/sample_deletion_requests.csv', encoding='utf-8'))}
sample_out = {r['case_id']: r for r in csv.DictReader(open('dataset/sample_output.csv', encoding='utf-8'))}

# Print each case's steps and why they exist
for cid in sorted(sample_out.keys())[:10]:
    out = sample_out[cid]
    req = sample_reqs[cid]
    steps = json.loads(out['steps_json'])
    print(f"=== {cid}: {out['deletion_status']} ===")
    print(f"  Email: {req['email']} | Req: {req['requested_at']} | Rep: {req['reported_at']} | Aud: {req['audit_at']}")
    print(f"  Text: {req['request_text']}")
    for s in steps:
        print(f"    {s['step_no']}. {s['phase']} | {s['system_id']} | {s['resource_id']} | {s['operation']} | {s['state']} | {s['evidence_id']}")
