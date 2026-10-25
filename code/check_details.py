import csv, re

system_activity = list(csv.DictReader(open('dataset/system_activity.csv', encoding='utf-8')))
details_patterns = set()
emails_in_details = []
users_in_details = []

for r in system_activity:
    d = r['details']
    # Check for email
    em = re.findall(r'[\w\.-]+@[\w\.-]+', d)
    if em:
        emails_in_details.append((r['activity_id'], r['resource_id'], em))
    uid = re.findall(r'user_\d+', d)
    if uid:
        users_in_details.append((r['activity_id'], r['resource_id'], uid))

print(f"Activities with email in details: {len(emails_in_details)}")
for x in emails_in_details[:10]:
    print("  ", x)

print(f"Activities with user_id in details: {len(users_in_details)}")
for x in users_in_details[:10]:
    print("  ", x)
