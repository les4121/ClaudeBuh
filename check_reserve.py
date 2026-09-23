import json
d = json.load(open(r"C:\pb\kirillov_2026-08.json", encoding="utf-8"))
seen = set()
cnt = 0
for r in d:
    o = r["opis"] or ""
    if o.startswith("Перевод собственных средств.") and "на счет" not in o.lower() and "на счёт" not in o.lower():
        seen.add((r["recv_name"], r["recv_inn"]))
        cnt += 1
print("без 'на счет':", cnt, "получатели:", seen)
