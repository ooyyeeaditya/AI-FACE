import urllib.request
import json

req = urllib.request.urlopen('http://127.0.0.1:5050/api/specimens')
data = json.loads(req.read().decode())
print(f"Total Preloaded Specimens: {len(data['specimens'])}")
print("-" * 80)

for s in data['specimens']:
    post_data = json.dumps({
        'doc_filename': s['doc_filename'],
        'live_filename': s['live_filename']
    }).encode('utf-8')
    r = urllib.request.Request('http://127.0.0.1:5050/api/screen', data=post_data, headers={'Content-Type': 'application/json'})
    resp = json.loads(urllib.request.urlopen(r).read().decode())
    score = resp['risk_score']
    verdict = resp['verdict']
    reasons = resp['reasons']
    print(f"{s['name']:<40} -> Risk: {score:>3}/100 [{verdict:<6}] | Flags: {len(reasons)}")
    if reasons:
        for reason in reasons:
            print(f"    - {reason}")
