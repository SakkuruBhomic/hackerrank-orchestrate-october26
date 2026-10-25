import csv
import re

with open("dataset/evidence_files.csv", encoding="utf-8") as f:
    files = list(csv.DictReader(f))

pdfs = [f for f in files if f["file_path"].endswith(".pdf")]
print(f"Total PDFs: {len(pdfs)}")
for p in pdfs:
    print(p["file_id"], p["file_path"])
    with open("dataset/" + p["file_path"], "rb") as f:
        data = f.read()
    print("  Size:", len(data))
    # Look for text streams or uncompressed text
    strings = re.findall(b"[a-zA-Z0-9_.@+-]{4,}", data)
    print("  Some strings:", strings[:15])
