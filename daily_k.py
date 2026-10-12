"""Таблица дня по выписке Кириллова: автоклассификация, проверка дублей в МойСклад,
исключение возвращённых Avito-покупок.
python daily_k.py <statement.json> <dd.mm.yyyy | all | refunds> [--since yyyy-mm-dd] [--emit out.json]
                  [--set "row=Контрагент|Статья|описание" ...]
--emit  записывает файл проводки для ms.py post (только строки дня «к проводке» с известными контрагентом и статьёй)
--set   вручную задаёт контрагента/статью/описание строки (контрагент или сотрудник из ids.py)"""
import datetime, json, re, sys
sys.path.insert(0, r"C:\pb")
import ms
import rules_k
import ids

stmt, day = sys.argv[1], sys.argv[2]
since = "2026-08-01"
emit_path = None
overrides = {}
_a = sys.argv[3:]
while _a:
    t = _a.pop(0)
    if t == "--since":
        since = _a.pop(0)
    elif t == "--emit":
        emit_path = _a.pop(0)
    elif t == "--set":
        row, rest = _a.pop(0).split("=", 1)
        parts = rest.split("|")
        overrides[int(row)] = parts
recs = json.load(open(stmt, encoding="utf-8"))


def pdate(s):
    d, m, y = s.split(".")
    return datetime.date(int(y), int(m), int(d))


def dkey(s):
    return pdate(s)


# --- существующие документы по счёту «Кириллов»
existing, off = [], 0
while True:
    d = ms.req("GET", "/entity/paymentout", {"limit": 100, "offset": off, "order": "moment,asc",
                                              "filter": f"moment>={since} 00:00:00",
                                              "expand": "organizationAccount,agent"})
    existing += d["rows"]
    off += 100
    if off >= d["meta"]["size"]:
        break
existing = [x for x in existing if ((x.get("organizationAccount") or {}).get("accountNumber") or "").strip() == "Кириллов"]
used_docs = set()


def find_existing(r):
    kop = round(r["debit"] * 100)
    ad = pdate(r["date_auth"])
    for x in existing:
        if x["id"] in used_docs or x["sum"] != kop:
            continue
        dd = (datetime.date.fromisoformat(x["moment"][:10]) - ad).days
        if 0 <= dd <= 7:
            used_docs.add(x["id"])
            return x
    return None


# --- возвраты/отмены Avito: сопоставление с покупками (по сумме и мерчанту)
RE_REFUND = re.compile(r"возврат средств по (?:операции )?оплат|отмена операции оплаты")


def merch_credit(o):
    m = re.search(r"оплат[ыеу]\s+(.*)$", o.lower())
    return re.sub(r"\s+", " ", m.group(1)).strip(" .") if m else ""


def merch_debit(o):
    m = re.match(r"оплата в\s+(.*)$", o.lower())
    return re.sub(r"\s+", " ", m.group(1)).strip(" .") if m else ""


refunds = [r for r in recs if r["type"] == "Кредит" and RE_REFUND.search((r["opis"] or "").lower())]
refunded_debit = {}   # debit row -> credit row
unmatched_refunds = []
debits = [r for r in recs if r["type"] == "Дебет"]
for c in sorted(refunds, key=lambda x: (dkey(x["date_auth"]), x["row"])):
    cands = [d for d in debits
             if d["row"] not in refunded_debit and round(d["debit"] * 100) == round(c["credit"] * 100)
             and merch_debit(d["opis"] or "") == merch_credit(c["opis"] or "")
             and dkey(d["date_auth"]) <= dkey(c["date_auth"])]
    if cands:
        best = max(cands, key=lambda d: (dkey(d["date_auth"]), d["row"]))
        refunded_debit[best["row"]] = c
    else:
        unmatched_refunds.append(c)

if day == "refunds":
    print(f"возвратов/отмен: {len(refunds)}; сопоставлено с покупками в выписке: {len(refunded_debit)}")
    tot = 0.0
    for drow, c in sorted(refunded_debit.items(), key=lambda t: t[0]):
        d = next(x for x in debits if x["row"] == drow)
        tot += d["debit"]
        print(f'  покупка #{drow} {d["date_auth"]} {d["debit"]:>10,.2f}  <- возврат #{c["row"]} {c["date_auth"]}')
    print(f"  сумма возвращённых покупок: {tot:,.2f}")
    print(f"без пары в выписке: {len(unmatched_refunds)}")
    for c in unmatched_refunds:
        kop = round(c["credit"] * 100)
        cand = [f'№{x["name"]} {x["moment"][:10]}' for x in existing if x["sum"] == kop and
                (x.get("agent") or {}).get("name") in ("авито закупка",)]
        print(f'  возврат #{c["row"]} {c["date_auth"]} {c["credit"]:>10,.2f} :: {c["opis"][:60]} | в МойСклад: {", ".join(cand) or "нет"}')
    sys.exit(0)

# --- таблица дня
rows = []
for r in sorted(recs, key=lambda x: (dkey(x["date_auth"] or "01.01.2000"), x["row"])):
    c = rules_k.classify(r)
    if r["row"] in overrides and r["type"] == "Дебет":
        p = overrides[r["row"]]
        c = {"skip": False, "cp": p[0], "art": p[1], "conf": "польз.", "note": "указано пользователем",
             "desc": p[2] if len(p) > 2 and p[2] else None}
    ex = None
    if not c["skip"] and r["row"] in refunded_debit:
        cr = refunded_debit[r["row"]]
        c = {"skip": True, "cp": "", "art": "", "conf": "",
             "note": "возвращена (возврат #%d %s) — не учитываем" % (cr["row"], cr["date_auth"])}
        ex = find_existing(r)  # если уже проведена — надо будет удалить
        if ex:
            c["note"] += f" ⚠ УЖЕ проведена №{ex['name']}"
    elif not c["skip"]:
        ex = find_existing(r)
    if c["skip"] and r["type"] == "Кредит" and RE_REFUND.search((r["opis"] or "").lower()):
        c = dict(c, note="возврат Avito (учтён с покупкой)")
    rows.append((r, c, ex))

sel = rows if day == "all" else [t for t in rows if t[0]["date_auth"] == day]
to_emit = []
cur = None
n_todo = 0
tot_todo = 0.0
skip_info = {}
for r, c, ex in sel:
    if c["skip"]:
        key = re.sub(r"\(возврат #\d+ [\d.]+\)", "", c["note"]) if "возвращена" in c["note"] else c["note"]
        s = skip_info.setdefault(key, [0, 0.0])
        s[0] += 1
        s[1] += r["amount"]
        if "⚠" in c["note"] or day != "all":
            if "возвращена" in c["note"]:
                print(f'  [не учитываем] #{r["row"]} {r["date_auth"]} {r["debit"]:,.2f} {r["opis"][:40]} :: {c["note"]}')
        continue
    if r["date_auth"] != cur:
        cur = r["date_auth"]
        print(f"\n===== {cur} =====")
    mark = f'УЖЕ №{ex["name"]} ({ex["moment"][:10]})' if ex else c["note"]
    if not ex:
        n_todo += 1
        tot_todo += r["debit"]
        to_emit.append((r, c))
    print(f'#{r["row"]:>3} | {r["debit"]:>11,.2f} | {r["opis"][:46]:46} | {c["cp"]:<20} | {c["art"]:<20} | {c["conf"]:<3} | {mark}')
print(f"\nк проводке: {n_todo} оп., {tot_todo:,.2f}")
for k, (n, s) in skip_info.items():
    print(f"пропуск: {k}: {n} шт., {s:,.2f}")


def default_desc(r):
    o = (r["opis"] or "").strip()
    m = re.search(r"от (\d\d\.\d\d\.\d{4})", o)
    if "комиссия за операции по терминалам эквайринга" in o.lower() and m:
        return f"Комиссия за операции по терминалам эквайринга от {m.group(1)}"
    o = re.split(r",\s*в т\.ч\.", o)[0]
    o = re.sub(r"\s*НДС не облагается.*$", "", o).strip(" .")
    return o[:100]


if emit_path:
    ops, unresolved = [], []
    for r, c in to_emit:
        cp, art = c["cp"], c["art"]
        if cp in ("?", "") or art in ("?", "") or cp.endswith("?") or art.endswith("?"):
            unresolved.append(r["row"])
            continue
        if cp in ids.EMP:
            atype, aid = "employee", ids.EMP[cp]
        elif cp in ids.CP:
            atype, aid = "counterparty", ids.CP[cp]
        else:
            unresolved.append(r["row"])
            print(f"!! неизвестный контрагент «{cp}» (строка {r['row']}) — добавь в ids.py")
            continue
        if art not in ids.EXP:
            unresolved.append(r["row"])
            print(f"!! неизвестная статья «{art}» (строка {r['row']}) — добавь в ids.py")
            continue
        d, m, y = r["date_auth"].split(".")
        ops.append({"row": r["row"], "agent_type": atype, "agent_id": aid, "expense_id": ids.EXP[art],
                    "account_id": ids.ACC_KIRILLOV, "sum_kop": round(r["debit"] * 100),
                    "moment": f"{y}-{m}-{d} 00:00:00", "description": c.get("desc") or default_desc(r)})
    json.dump(ops, open(emit_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"записано в {emit_path}: {len(ops)} оп.; не разобрано: {unresolved or 'нет'}")
