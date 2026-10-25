import csv

system_activity = list(csv.DictReader(open('dataset/system_activity.csv', encoding='utf-8')))
worker_acts = [a for a in system_activity if a['source_system'] == 'deletion_worker']
print(f"Total deletion_worker activities: {len(worker_acts)}")

# Group activities into batches by time (e.g. gaps > 1 hour)
batches = []
cur_batch = []
for a in worker_acts:
    if not cur_batch:
        cur_batch.append(a)
    else:
        # compare times
        from datetime import datetime
        t1 = datetime.fromisoformat(cur_batch[-1]['event_time'].replace('Z', '+00:00'))
        t2 = datetime.fromisoformat(a['event_time'].replace('Z', '+00:00'))
        if (t2 - t1).total_seconds() > 3600 * 2:  # 2 hours gap
            batches.append(cur_batch)
            cur_batch = [a]
        else:
            cur_batch.append(a)
if cur_batch:
    batches.append(cur_batch)

print(f"Total deletion worker batches: {len(batches)}")
for i, b in enumerate(batches[:15]):
    t_start = b[0]['event_time']
    t_end = b[-1]['event_time']
    targets = [a['target_system'] for a in b]
    res_ids = [a['resource_id'] for a in b]
    print(f"Batch {i+1}: {t_start} to {t_end} ({len(b)} events) targets: {set(targets)}")
    print(f"   res_ids: {res_ids[:6]}")
