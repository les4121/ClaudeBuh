import json

recs = json.load(open(r"C:\pb\kirillov_2026-08.json", encoding="utf-8"))

def is_reserve(o):
    ol = (o or "").lower()
    return (o or "").startswith("Перевод собственных средств.") and "на счет" not in ol and "на счёт" not in ol

def is_vozvrat(o):
    return "возврат средств по терминалам эквайринга" in (o or "").lower()

candidates = []
skipped_reserve = 0
skipped_vozvrat = 0
for r in recs:
    if r["type"] != "Дебет":
        continue
    o = r["opis"]
    if is_reserve(o):
        skipped_reserve += 1
        continue
    if is_vozvrat(o):
        skipped_vozvrat += 1
        continue
    candidates.append(r["row"])

posted = set()
for l in open(r"C:\pb\posted_kirillov.jsonl", encoding="utf-8"):
    if l.strip():
        posted.add(json.loads(l)["row"])

print(f"Всего Дебет: {sum(1 for r in recs if r['type']=='Дебет')}")
print(f"Пропущено (резервный фонд): {skipped_reserve}")
print(f"Пропущено (возврат по терминалам): {skipped_vozvrat}")
print(f"Кандидатов к проводке: {len(candidates)}")
print(f"Проведено (в ledger): {len(posted)}")
missing = sorted(set(candidates) - posted)
extra = sorted(posted - set(candidates))
print("Не проведено (расхождение):", missing)
print("В ledger, но не кандидат (расхождение):", extra)

total = 0
for l in open(r"C:\pb\posted_kirillov.jsonl", encoding="utf-8"):
    if l.strip():
        total += json.loads(l)["sum"]
print(f"Сумма проведено: {total/100:,.2f}")
