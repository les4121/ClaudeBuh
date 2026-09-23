import sys, json

recs = json.load(open(sys.argv[1], encoding="utf-8"))
from_day = sys.argv[2] if len(sys.argv) > 2 else None  # dd.mm.yyyy, inclusive

EXP = {
    "Закупка товаров": "8dbf9374-0a01-11e4-b9bf-002590a32f46",
    "Закупка запчастей": "3c04fcb0-d1cc-11f0-0a80-1be4000d188e",
    "Маркетинг и реклама": "41bfa95c-3a48-11e8-9109-f8fc000248c4",
    "Транспортные расходы": "d73e7b2e-d406-11f0-0a80-1a6b002b89d1",
    "банковские расходы": "50c3605a-e329-11f0-0a80-1b84001c8065",
    "хозяйственные расходы": "7b017637-e327-11f0-0a80-0c37001d21f6",
    "Аренда": "41beb637-3a48-11e8-9109-f8fc000248c2",
    "Зарплата": "41bf52da-3a48-11e8-9109-f8fc000248c3",
    "Налоги и сборы": "8dbf9a86-0a01-11e4-a190-002590a32f46",
    "Диски и опера": "4062f1df-37fd-11f1-0a80-01c6004684bf",
    "Иван Кириллов": "524dc438-e333-11f0-0a80-1a22001c99b0",
    "неясно": "196fdf43-e32a-11f0-0a80-13a9001cd769",
}
CP = {
    "Т-банк": "26c0437d-e329-11f0-0a80-0e10001cf39d",
    "Авито реклама": "bb77371e-d405-11f0-0a80-08b0002b1d1f",
    "авито закупка": "53f6ce93-eb99-11f0-0a80-18d1008510c6",
    "Иван Кириллов": "57530279-d5e2-11f0-0a80-08b40014a1fc",
    "Древо": "9775fa03-38ec-11f1-0a80-107000257720",
    "ИП Трофименко Валентин Викторович": "bbb2aaa2-e4e9-11f0-0a80-0714003e9cdd",
    "ии агент": "80106a57-7872-11f1-0a80-0b550059e287",
    "Insales": "ebabb9a4-d408-11f0-0a80-0df7002d054e",
    "Аренда офиса Козупеев": "cfd7c5f6-d407-11f0-0a80-08b0002ba416",
    "Закуп": "d742029f-f520-11ec-0a80-0d88000e0a79",
}


def dkey(s):
    d, m, y = s.split(".")
    return (y, m, d)


def classify(r):
    o = r["opis"] or ""
    ol = o.lower()
    if r["type"] != "Дебет":
        return None
    if o.startswith("Перевод собственных средств.") and "на счет" not in ol and "на счёт" not in ol:
        return None  # П12 резервный фонд
    if "возврат средств по терминалам эквайринга" in ol:
        return None  # П14
    if "комиссия за операции по терминалам эквайринга" in ol or \
       "плата за пакет" in ol or "плата за обслуживание" in ol or \
       "комиссия за внешний банковский перевод" in ol or "плата за использованный лимит овердрафта" in ol or \
       "плата за активный овердрафт" in ol or "оповещение об операциях" in ol or \
       "бухгалтерское обслуживание" in ol:
        return ("Т-банк", "банковские расходы", "выс", "П5")
    if "vkusvill" in ol or "onetwotrip" in ol or ol.startswith("оплата в ekc ") or "sber life insur" in ol:
        return ("Иван Кириллов", "Иван Кириллов", "выс", "П13")
    if "аренда" in ol:
        return ("Аренда офиса Козупеев", "Аренда", "ср", "уточнить получателя")
    if "трофименко" in (r["recv_name"] or "").lower():
        return ("ИП Трофименко Валентин Викторович", "Маркетинг и реклама", "выс", "П9")
    if "программист" in ol or "разработчик" in ol:
        return ("? (программист)", "Маркетинг и реклама", "ср", "уточнить контрагента")
    if "insales" in ol:
        return ("Insales", "Маркетинг и реклама", "выс", "правило")
    if "avito" in ol and "dostavka" not in ol:
        amt = r["debit"]
        conf = "ср" if amt % 1000 == 0 else "низ"
        return ("Авито реклама", "Маркетинг и реклама", conf, "П8" if conf == "ср" else "сумма неровная — проверить")
    if "avito" in ol and "dostavka" in ol:
        return ("авито закупка", "Закупка товаров", "ср", "П8 Доставка")
    if "перевод собственных средств на счет" in ol:
        return ("Иван Кириллов?", "Иван Кириллов?", "низ", "П6 — САМОЕ ЧАСТОЕ: Иван Кириллов, но проверить (бывали искл.: зарплата/закупка)")
    if "аусн" in ol or "енп" in ol:
        return ("ФНС", "Налоги и сборы", "выс", "")
    return ("???", "???", "низ", "НЕТ ПРАВИЛА")


rows = []
for r in recs:
    c = classify(r)
    if c is None:
        continue
    if from_day and dkey(r["date_auth"]) < dkey(from_day):
        continue
    cp, art, conf, note = c
    rows.append({**r, "cp": cp, "art": art, "conf": conf, "note": note})

cur = None
tot = 0.0
for r in sorted(rows, key=lambda x: (dkey(x["date_auth"]), x["row"])):
    if r["date_auth"] != cur:
        cur = r["date_auth"]
        print(f"\n===== {cur} =====")
    tot += r["debit"]
    print(f'#{r["row"]:>3} | {r["debit"]:>10,.2f} | {r["opis"][:50]:50} | '
          f'{r["cp"]:<20} | {r["art"]:<18} | {r["conf"]:<3} | {r["note"]}')

print(f"\nИтого: {len(rows)} операций, {tot:,.2f}")
