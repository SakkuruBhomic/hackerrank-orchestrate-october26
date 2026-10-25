import re
import sys
import zlib
sys.stdout.reconfigure(encoding="utf-8")

def read_pdf(path):
    with open(path, "rb") as f:
        data = f.read()

    # Find all obj ... endobj
    for m in re.finditer(rb"(\d+ \d+ obj.*?endobj)", data, re.DOTALL):
        obj = m.group(1)
        if b"stream" not in obj:
            continue
        # get length
        len_m = re.search(rb"/Length\s+(\d+)", obj)
        stream_idx = obj.find(b"stream")
        start = stream_idx + 6
        while start < len(obj) and obj[start] in (10, 13):
            start += 1
        if len_m:
            length = int(len_m.group(1))
            stream_data = obj[start:start+length]
        else:
            end = obj.find(b"endstream", start)
            stream_data = obj[start:end].rstrip(b"\r\n")

        # filter
        is_flate = b"FlateDecode" in obj
        if is_flate:
            try:
                dec = zlib.decompress(stream_data)
            except Exception:
                try:
                    dec = zlib.decompress(stream_data, -15)
                except Exception:
                    continue
        else:
            dec = stream_data

        # Check if decompressed data contains text
        # In PDF, text is often in Tj or TJ or text strings
        text_matches = re.findall(rb"\((.*?)\)", dec)
        if text_matches:
            extracted = [t.decode("latin1", errors="ignore") for t in text_matches if len(t) > 1]
            if extracted:
                print(f"--- Object in {path} ---")
                print(" ".join(extracted)[:300])

for p in [
    "dataset/evidence/documents/account_history_report_20260718.pdf",
    "dataset/evidence/documents/legal_retention_register_20260529.pdf",
    "dataset/evidence/documents/security_retention_extract.pdf",
    "dataset/evidence/documents/delivery_correction_attachment.pdf",
]:
    read_pdf(p)
