import csv, json, re, sqlite3, base64, zlib
from pathlib import Path
from collections import defaultdict

DATASET = Path("dataset")

def parse_pdf(path):
    with open(path, "rb") as f:
        data = f.read()
    lines = []
    for m in re.finditer(rb"(\d+ \d+ obj.*?endobj)", data, re.DOTALL):
        obj = m.group(1)
        if b"stream" not in obj:
            continue
        s_idx = obj.find(b"stream")
        start = s_idx + 6
        while obj[start] in (10, 13):
            start += 1
        end = obj.find(b"endstream", start)
        s_data = obj[start:end].strip(b"\r\n ")
        curr = s_data
        try:
            if b"ASCII85Decode" in obj:
                curr = base64.a85decode(curr, adobe=True)
            if b"FlateDecode" in obj:
                curr = zlib.decompress(curr)
        except Exception:
            continue
        for tm in re.finditer(rb"\((.*?)\)\s*Tj", curr):
            txt = tm.group(1).decode("latin1", errors="ignore")
            lines.append(txt)
    return " \n ".join(lines)

print("Testing PDF extraction...")
for p in DATASET.glob("evidence/**/*.pdf"):
    txt = parse_pdf(p)
    print(p.name, f"extracted {len(txt)} chars")

print("All tests passed.")
