import os, sys, json, urllib.request, gzip
TOKEN = os.environ["MS_TOKEN"]
BASE = "https://api.moysklad.ru/api/remap/1.2"
needle = sys.argv[1].lower()
off = 0
found = []
total = None
while True:
    r = urllib.request.Request(f"{BASE}/entity/counterparty?limit=1000&offset={off}")
    r.add_header("Authorization", "Bearer " + TOKEN)
    r.add_header("Accept-Encoding", "gzip")
    raw = urllib.request.urlopen(r).read()
    try:
        raw = gzip.decompress(raw)
    except Exception:
        pass
    d = json.loads(raw.decode("utf-8-sig"))
    total = d["meta"]["size"]
    for x in d["rows"]:
        nm = (x.get("name") or "")
        if needle in nm.lower():
            found.append((x["id"], nm, x.get("archived"), x.get("companyType"), x.get("inn")))
    off += 1000
    if off >= total:
        break
print(f"просканировано {total} контрагентов, совпадений: {len(found)}")
for f in found:
    print(f"{f[0]} | {f[1]!r} | archived={f[2]} | {f[3]} | inn={f[4]}")
