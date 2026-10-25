import base64, zlib, re

def parse_pdf_text(path):
    with open(path, "rb") as f:
        data = f.read()

    lines = []
    # Find all obj ... endobj with streams
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
        
        # Check filters
        filters = []
        f_m = re.search(rb"/Filter\s*(\[[^\]]+\]|/[a-zA-Z0-9]+)", obj)
        if f_m:
            f_str = f_m.group(1)
            if b"ASCII85Decode" in f_str:
                filters.append("a85")
            if b"FlateDecode" in f_str:
                filters.append("flate")

        curr = s_data
        try:
            if "a85" in filters:
                curr = base64.a85decode(curr, adobe=True)
            if "flate" in filters:
                curr = zlib.decompress(curr)
        except Exception:
            continue

        # Extract all text inside parentheses: (Text) Tj or (Text)
        for tm in re.finditer(rb"\((.*?)\)\s*Tj", curr):
            txt = tm.group(1).decode("latin1", errors="ignore")
            lines.append(txt)
    return lines

for eid, p in [
    ("evidence_18", "dataset/evidence/documents/account_history_report_20260718.pdf"),
    ("evidence_27", "dataset/evidence/documents/legal_retention_register_20260529.pdf"),
    ("evidence_55", "dataset/evidence/documents/security_retention_extract.pdf"),
    ("evidence_58", "dataset/evidence/documents/delivery_correction_attachment.pdf"),
]:
    lines = parse_pdf_text(p)
    print(f"=== {eid} ({p}) ===")
    print("Found lines:", len(lines))
    for l in lines[:15]:
        print("  ", l)
