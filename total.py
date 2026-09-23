import json
n, total = 0, 0
for l in open(r"C:\pb\posted_davydov.jsonl", encoding="utf-8"):
    if l.strip():
        n += 1
        total += json.loads(l)["sum"]
print(f"Документов: {n}, сумма: {total/100:,.2f} руб.")
