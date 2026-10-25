import csv, json

sample_reqs = list(csv.DictReader(open('dataset/sample_deletion_requests.csv', encoding='utf-8')))
sample_out = {r['case_id']: r for r in csv.DictReader(open('dataset/sample_output.csv', encoding='utf-8'))}

for r in sample_reqs:
    cid = r['case_id']
    out = sample_out[cid]
    steps = json.loads(out['steps_json'])
    accts = [s['resource_id'] for s in steps if s['system_id'] == 'account_service']
    all_res = [s['resource_id'] for s in steps]
    eids = [s['evidence_id'] for s in steps if s['evidence_id']]
    print(f"{cid:7} | req={r['requested_at'][:10]} rep={r['reported_at'][:10]} aud={r['audit_at'][:10]} | {out['deletion_status']:11} | accts={accts} | eids={set(eids)}")
