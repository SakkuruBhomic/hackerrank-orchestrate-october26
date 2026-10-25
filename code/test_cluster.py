import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from main import parse_ts, SERVICE_SYSTEM_MAP

DATASET = Path("dataset")

# 1. Load system activity worker acts
worker_acts = []
with open(DATASET / "system_activity.csv", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        if row["source_system"] == "deletion_worker":
            worker_acts.append(row)

# Cluster into batches by account_service
clusters = []
curr_cluster = None
for a in worker_acts:
    if a["target_system"] == "account_service" and "submitted" in a["details"]:
        if curr_cluster:
            clusters.append(curr_cluster)
        curr_cluster = {"account": a["resource_id"], "time": a["event_time"], "resources": {a["resource_id"]}}
    elif curr_cluster:
        # Check time gap: if more than 3 hours, close cluster
        dt = (parse_ts(a["event_time"]) - parse_ts(curr_cluster["time"])).total_seconds()
        if dt > 10800:
            clusters.append(curr_cluster)
            curr_cluster = None
        else:
            curr_cluster["resources"].add(a["resource_id"])
if curr_cluster:
    clusters.append(curr_cluster)

print(f"Formed {len(clusters)} worker clusters.")
for c in clusters:
    if any(r in c["resources"] for r in ["account_5482", "account_3866", "account_7012", "account_8858", "account_4857"]):
        print(c["account"], c["time"], c["resources"])
