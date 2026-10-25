from pathlib import Path
import re

print("Checking PDFs...")
import base64, zlib
for p in Path('dataset/evidence/documents').glob('*.pdf'):
    data = p.read_bytes()
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
    txt = " ".join(lines)
    if '6645' in txt:
        print(f"6645 in PDF {p.name}")
    if '5569' in txt:
        print(f"5569 in PDF {p.name}")

print("Checking PNGs in system_activity.csv...")
import csv
for r in csv.DictReader(open('dataset/system_activity.csv', encoding='utf-8')):
    if any(k in str(r) for k in ['6645', '5569', 'user_50', 'user_49', 'user_48']):
        print(r['activity_id'], r['event_type'], r['target_system'], r['resource_id'], r['details'])
