import csv, json

sample_reqs = {r['case_id']: r for r in csv.DictReader(open('dataset/sample_deletion_requests.csv', encoding='utf-8'))}
sample_out = {r['case_id']: r for r in csv.DictReader(open('dataset/sample_output.csv', encoding='utf-8'))}
system_activity = list(csv.DictReader(open('dataset/system_activity.csv', encoding='utf-8')))

for cid, out in sorted(sample_out.items()):
    req = sample_reqs[cid]
    steps = json.loads(out['steps_json'])
    res_ids = {s['resource_id'] for s in steps}
    
    # Find matching activities for these resource IDs
    acts = [a for a in system_activity if a['resource_id'] in res_ids]
    print(f"=== {cid} ({out['deletion_status']}) ===")
    print(f"  Req: requested_at={req['requested_at']}, reported_at={req['reported_at']}")
    print(f"  Steps resources: {sorted(res_ids)}")
    print(f"  Matched {len(acts)} activities:")
    for a in acts:
        print(f"    act_id={a['activity_id']} time={a['event_time']} src={a['source_system']} tgt={a['target_system']} res={a['resource_id']} op={a['event_type']} res={a['reported_result']}")
