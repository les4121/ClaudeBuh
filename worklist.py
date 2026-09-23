"""Строит рабочий список расходов по правилам П1-П6 и предлагает разметку."""
import sys, json, re

recs = json.load(open(sys.argv[1], encoding="utf-8"))
show = sys.argv[2] if len(sys.argv) > 2 else "all"   # all | <dd.mm.yyyy> | <dd.mm>-<dd.mm>

MONTH = "08.2026"

# ---- статьи расходов: имя -> id ----
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
    "неясно": "196fdf43-e32a-11f0-0a80-13a9001cd769",
}

def classify(r):
    """-> (контрагент, статья, уверенность, комментарий) или None если пропускаем"""
    o = (r["opis"] or "")
    ol = o.lower()
    mcc = r["mcc"] or ""

    # --- П4: только расходы
    if r["type"] != "Дебет":
        return None
    # --- П3: только август по дате авторизации
    if not r["date_auth"] or not r["date_auth"].endswith(MONTH):
        return None
    # --- П5: овердрафт-механика
    if "погашение разрешенного овердрафта" in ol or "предоставление" in ol and "овердрафт" in ol:
        return None

    # --- банковские расходы (П5 + обычные комиссии)
    if any(s in ol for s in [
        "комиссия за внешний банковский перевод",
        "плата за активный овердрафт",
        "плата за использованный лимит овердрафта",
        "плата за обслуживание счета",
        'плата за пакет',
        "доплата до минимального платежа за операции по терминалам",
        "комиссия за операции по терминалам эквайринга",
        "оповещение об операциях",
    ]):
        return ("Т-банк", "банковские расходы", "выс", "П5 / комиссия банка")

    # --- переводы себе: П6, разбираем вручную
    if "перевод собственных средств" in ol:
        return ("Давыдов Иван", "??? (П6 — вручную)", "—", "перевод себе на карту, решаем отдельно")

    # --- налоги
    if "енп" in ol or "налог по аусн" in ol or ("налог" in ol and "аусн" in ol):
        return ("ФНС", "Налоги и сборы", "выс", "налоговый платёж")

    # --- карточные мерчанты
    m = r["merchant"] or ""
    ml = m.lower()
    if "dns" in ol or "dns" in ml:
        return ("DNS", "Закупка запчастей", "выс", "по прошлым периодам")
    if "ozon" in ol or "озон" in ol:
        return ("озон", "Закупка запчастей", "ср", "OZON — уточнить: запчасти или товары")
    if "avito dostavka" in ol or "tbank-avito dostavka" in ol or "ym*avito dostavka" in ol:
        return ("авито закупка", "Закупка товаров", "ср", "Авито Доставка = закупка товара")
    if "tbank-avito" in ol or "ym*avito" in ol or ("avito" in ol and "dostavka" not in ol):
        return ("Авито реклама", "Маркетинг и реклама", "низ", "Avito без 'Доставка' — реклама? уточнить")
    if "yandex" in ol and "dostavka" in ol:
        return ("яндексдоставка", "Транспортные расходы", "выс", "Яндекс Доставка")
    if "yandex" in ol and ("*go" in ol or mcc == "3990"):
        return ("яндекс карты", "Транспортные расходы", "выс", "такси")
    if "yandex" in ol:
        return ("яндекс карты", "Транспортные расходы", "низ", "Яндекс — уточнить сервис")
    if "onlayn treyd" in ol or "онлайнтрейд" in ol:
        return ("ОнлайнТрейд", "Закупка товаров", "низ", "электроника — товары или запчасти?")
    if "aliexpress" in ol or "pt*aliexpress" in ol:
        return ("AliExpress", "Закупка запчастей", "низ", "уточнить")
    if "pyaterochka" in ol or "пятерочка" in ol:
        return ("Пятёрочка", "хозяйственные расходы", "низ", "продукты/хознужды?")
    if "бухгалтерское обслуживание" in ol:
        return ("Бухгалтер", "хозяйственные расходы", "низ", "нет статьи 'бухуслуги' — уточнить")
    if "образовательные услуги" in ol:
        return ("?", "неясно", "низ", "образовательные услуги — уточнить")
    if "стоянк" in ol or "парковк" in ol:
        return ("Стоянка", "Транспортные расходы", "низ", "стоянка/парковка")
    if "аренд" in ol:
        return ("?", "Аренда", "ср", "аренда — уточнить контрагента")
    if "aviasales" in ol or "aviasales" in ml or "yunigeit" in ol:
        return ("Aviasales", "Транспортные расходы", "низ", "билеты/командировка?")

    # --- банковский перевод по счёту юрлицу/ИП
    if "оплата по счёт" in ol or "оплата по счет" in ol or "оплата счёт" in ol or re.search(r"по договору", ol):
        cp = r["recv_name"] or "?"
        return (cp, "неясно", "низ", f"перевод по счёту, ИНН получателя {r['recv_inn'] or '—'}")

    return ("?", "неясно", "низ", "нет правила — уточнить")


def dkey(s):
    d, m, y = s.split(".")
    return (y, m, d)

rows_out = []
for r in recs:
    c = classify(r)
    if c is None:
        continue
    cp, art, conf, note = c
    rows_out.append({**r, "cp": cp, "art": art, "conf": conf, "note": note})

# фильтр показа. форматы: all | dd | dd.mm | dd..dd | dd.mm..dd.mm
def full(x):
    n = x.count(".")
    if n == 2:
        return x
    if n == 1:
        return x + ".2026"
    return f"{int(x):02d}.{MONTH}"

if show != "all":
    if ".." in show:
        a, b = show.split("..")
        rows_out = [r for r in rows_out if dkey(full(a)) <= dkey(r["date_auth"]) <= dkey(full(b))]
    else:
        rows_out = [r for r in rows_out if r["date_auth"] == full(show)]

cur = None
tot = 0.0
for r in sorted(rows_out, key=lambda x: (dkey(x["date_auth"]), x["row"])):
    if r["date_auth"] != cur:
        cur = r["date_auth"]
        print(f"\n===== {cur} =====")
    tot += r["debit"]
    print(f'#{r["row"]:>3} | {r["debit"]:>10,.2f} | {r["opis"][:46]:46} | '
          f'{r["cp"]:<16} | {r["art"]:<22} | {r["conf"]:<3} | {r["note"]}')

print(f"\nИтого показано: {len(rows_out)} операций, сумма {tot:,.2f}")
