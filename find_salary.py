import os, json, urllib.request, gzip
TOKEN = os.environ["MS_TOKEN"]
BASE = "https://api.moysklad.ru/api/remap/1.2"
off = 0
seen = 0
hits = []
while off < 600:
    r = urllib.request.Request(f"{BASE}/entity/paymentout?limit=100&offset={off}&order=moment,desc&expand=agent,expenseItem")
    r.add_header("Authorization", "Bearer " + TOKEN)
    r.add_header("Accept-Encoding", "gzip")
    raw = urllib.request.urlopen(r).read()
    try: raw = gzip.decompress(raw)
    except Exception: pass
    d = json.loads(raw.decode("utf-8-sig"))
    for x in d["rows"]:
        seen += 1
        ei = (x.get("expenseItem") or {}).get("name")
        if ei == "Зарплата":
            a = x.get("agent") or {}
            m = a.get("meta", {})
            hits.append((x["name"], x["moment"][:10], a.get("name"), m.get("type"),
                         m.get("href", "").split("/entity/")[-1].split("?")[0]))
    off += 100
    if off >= d["meta"]["size"]:
        break
print(f"просмотрено {seen} платежей, зарплатных: {len(hits)}")
for h in hits[:40]:
    print(f"{h[0]:8} {h[1]}  {h[2]:20}  type={h[3]:12}  {h[4]}")
