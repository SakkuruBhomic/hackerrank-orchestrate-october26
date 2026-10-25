import csv

with open("dataset/evidence_files.csv", encoding="utf-8") as f:
    files = list(csv.DictReader(f))

for f in files[50:]:
    print(f["file_id"], f["captured_at"], f["file_path"], f["origin"])
