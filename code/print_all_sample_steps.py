import csv, json

sample_out = list(csv.DictReader(open('dataset/sample_output.csv', encoding='utf-8')))

for r in sample_out:
    cid = r['case_id']
    st = r['deletion_status']
    steps = json.loads(r['steps_json'])
    print(f"=== {cid} ({st}) [{len(steps)} steps] ===")
    for s in steps:
        print(f"  {s['step_no']}. {s['phase']:12} | {s['system_id']:20} | {s['resource_id']:18} | {s['operation']:25} | {s['state']:10} | eid={s['evidence_id']}")
