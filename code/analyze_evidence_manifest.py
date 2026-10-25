import csv
from collections import Counter

with open("dataset/evidence_files.csv", encoding="utf-8") as f:
    files = list(csv.DictReader(f))

print(f"Total evidence files: {len(files)}")
origins = Counter(r["origin"] for r in files)
print("Origins:")
for o, c in origins.items():
    print(f"  {o}: {c}")

exts = Counter(r["file_path"].split(".")[-1] for r in files)
print("Extensions:", exts)

# Print first 20 files
for f in files[:20]:
    print(f)
