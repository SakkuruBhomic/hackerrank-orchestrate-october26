import re
import zlib

def extract_pdf_streams(path):
    with open(path, "rb") as f:
        data = f.read()
    
    # find all stream ... endstream blocks
    streams = re.findall(b"stream[\r\n]+(.*?)[\r\n]+endstream", data, re.DOTALL)
    texts = []
    for s in streams:
        try:
            decomp = zlib.decompress(s)
            # find text in BT ... ET blocks or string literals ( ... )
            txts = re.findall(rb"\((.*?)\)", decomp)
            for t in txts:
                try:
                    texts.append(t.decode('utf-8', errors='ignore'))
                except Exception:
                    pass
        except Exception:
            pass
    return " ".join(texts)

for eid, p in [
    ("evidence_18", "dataset/evidence/documents/account_history_report_20260718.pdf"),
    ("evidence_27", "dataset/evidence/documents/legal_retention_register_20260529.pdf"),
    ("evidence_55", "dataset/evidence/documents/security_retention_extract.pdf"),
    ("evidence_58", "dataset/evidence/documents/delivery_correction_attachment.pdf"),
]:
    t = extract_pdf_streams(p)
    print(f"=== {eid} ({p}) ===")
    print(t[:500])
    print()
