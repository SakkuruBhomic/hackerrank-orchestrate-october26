import csv

manifest = list(csv.DictReader(open('dataset/evidence_files.csv', encoding='utf-8')))
for m in manifest:
    if m['file_path'].endswith('.png'):
        print(m['file_id'], m['file_path'])
