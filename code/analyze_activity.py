import csv
from collections import Counter

with open("dataset/system_activity.csv", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

print(f"Total rows in system_activity.csv: {len(rows)}")
event_types = Counter(r["event_type"] for r in rows)
print("Event types:", event_types)
source_systems = Counter(r["source_system"] for r in rows)
print("Source systems:", source_systems)
target_systems = Counter(r["target_system"] for r in rows)
print("Target systems:", target_systems)

# Check details samples
for r in rows[:10]:
    print(r)
