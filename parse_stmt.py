import sys, json, datetime, openpyxl

SRC = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else None

wb = openpyxl.load_workbook(SRC, data_only=True)
ws = wb.active
rows = list(ws.iter_rows(values_only=True))

# найти строку заголовка
hdr_idx = None
for i, r in enumerate(rows):
    if r and r[0] == "Номер счёта" and "Тип операции" in r:
        hdr_idx = i
        break
if hdr_idx is None:
    sys.exit("header row not found")
hdr = [(_ or "").strip() for _ in rows[hdr_idx]]
col = {name: j for j, name in enumerate(hdr)}

def g(r, name):
    j = col.get(name)
    if j is None or j >= len(r):
        return None
    v = r[j]
    if isinstance(v, str):
        v = v.strip()
    return v if v not in ("", None) else None

def d(v):
    if v is None:
        return None
    if isinstance(v, (datetime.datetime, datetime.date)):
        return v.strftime("%d.%m.%Y")
    return str(v).split()[0]

recs = []
for r in rows[hdr_idx + 1:]:
    if not r or g(r, "Номер счёта") is None or g(r, "Тип операции") is None:
        continue
    debit = g(r, "Дебет") or 0
    credit = g(r, "Кредит") or 0
    rec = {
        "row": None,
        "type": g(r, "Тип операции"),                 # Дебет=расход, Кредит=приход
        "date_auth": d(g(r, "Дата авторизации")),      # <-- базовая дата
        "date_provod": d(g(r, "Дата проведения")),
        "date_trans": d(g(r, "Дата транзакции")),
        "doc_no": g(r, "Номер документа"),
        "debit": float(debit),
        "credit": float(credit),
        "amount": float(debit) if float(debit) else float(credit),
        "opis": g(r, "Описание операции"),
        "purpose": g(r, "Назначение платежа"),
        "payer_name": g(r, "Наименование плательщика"),
        "payer_inn": g(r, "ИНН плательщика"),
        "recv_name": g(r, "Наименование получателя"),
        "recv_inn": g(r, "ИНН получателя"),
        "cp_name": g(r, "Наименование контрагента"),
        "cp_inn": g(r, "ИНН контрагента"),
        "card": g(r, "Номер карты"),
        "mcc": g(r, "MCC"),
        "merchant": g(r, "Банк"),                      # для карт. операций тут мерчант
        "city": g(r, "Место совершения (Город)"),
    }
    recs.append(rec)

for i, rec in enumerate(recs, 1):
    rec["row"] = i

if OUT:
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(recs, f, ensure_ascii=False, indent=1)

# ---- сводка ----
deb = [x for x in recs if x["type"] == "Дебет"]
cred = [x for x in recs if x["type"] == "Кредит"]
print(f"Всего операций: {len(recs)}   Дебет(расход): {len(deb)}   Кредит(приход): {len(cred)}")
print(f"Сумма дебета:  {sum(x['debit'] for x in recs):>14,.2f}")
print(f"Сумма кредита: {sum(x['credit'] for x in recs):>14,.2f}")
print(f"Диапазон дат авторизации: {min((x['date_auth'] or '—') for x in recs)} .. {max((x['date_auth'] or '—') for x in recs)}")
missing_auth = [x for x in recs if not x["date_auth"]]
print(f"Без даты авторизации: {len(missing_auth)} строк -> rows {[x['row'] for x in missing_auth]}")

from collections import Counter
def norm(s):
    s = (s or "").strip()
    for pref in ("Оплата в ", "Отражение операции оплаты по карте"):
        if s.startswith(pref):
            s = s[len(pref):]
    return s[:45]
print("\n-- топ 'Описание операции' (нормализованное), дебет --")
for k, n in Counter(norm(x["opis"]) for x in deb).most_common(40):
    print(f"{n:3}  {k}")
print("\n-- 'Описание операции', кредит --")
for k, n in Counter(norm(x["opis"]) for x in cred).most_common(20):
    print(f"{n:3}  {k}")
