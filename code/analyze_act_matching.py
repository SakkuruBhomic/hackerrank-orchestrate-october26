import csv, json

sample_reqs = list(csv.DictReader(open('dataset/sample_deletion_requests.csv', encoding='utf-8')))
sample_out = {r['case_id']: r for r in csv.DictReader(open('dataset/sample_output.csv', encoding='utf-8'))}
system_activity = list(csv.DictReader(open('dataset/system_activity.csv', encoding='utf-8')))

# Check all 32 cases and their resources in sample_output.csv
# and see which system_activity rows have those resource_ids
for req in sample_reqs:
    cid = req['case_id']
    steps = json.loads(sample_out[cid]['steps_json'])
    res_ids = {s['resource_id'] for s in steps}
    
    # Check matching activities
    matching = [a for a in system_activity if a['resource_id'] in res_ids]
    # Check if there are other activities at the exact same timestamp or batch
    print(f"{cid} ({req['email']}) -> res_ids: {res_ids}")
    for a in matching:
        print(f"   act={a['activity_id']} time={a['event_time']} {a['source_system']} -> {a['target_system']} {a['resource_id']} {a['event_type']} {a['reported_result']}")
