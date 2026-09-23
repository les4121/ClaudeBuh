#!/usr/bin/env python3
"""Компактный клиент МойСклад JSON API 1.2 для этапа обучения (только чтение + явная проводка).
HTTP-запросы идут через curl.exe (не urllib) — urllib на этой машине периодически
подвисает намертво на TLS-хендшейке, curl стабильно быстрый."""
import json
import os
import subprocess
import sys
import tempfile
import urllib.parse

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

BASE = "https://api.moysklad.ru/api/remap/1.2"
TOKEN = os.environ.get("MS_TOKEN", "").strip()

ORG_IP = "41b8770c-3a48-11e8-9109-f8fc000248b6"          # ИП Кириллов Иван Евгеньевич
ORG_ACC_DEFAULT = "41b87d60-3a48-11e8-9109-f8fc000248b7"  # расчётный счёт по умолчанию


def req(method, path, params=None, body=None, timeout=25):
    url = path if path.startswith("http") else BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    cmd = ["curl.exe", "-sS", "--max-time", str(timeout), "-X", method,
           "-H", "Authorization: Bearer " + TOKEN,
           "-H", "Content-Type: application/json",
           "--compressed", "-w", "\n__HTTP_STATUS__%{http_code}"]
    tmp = None
    if body is not None:
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
        json.dump(body, tmp, ensure_ascii=False)
        tmp.close()
        cmd += ["--data-binary", f"@{tmp.name}"]
    cmd.append(url)
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=timeout + 10)
    finally:
        if tmp:
            os.unlink(tmp.name)
    if p.returncode != 0:
        print(f"CURL ERROR (exit {p.returncode}): {p.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    out = p.stdout
    marker = "__HTTP_STATUS__"
    idx = out.rfind(marker)
    status = int(out[idx + len(marker):].strip())
    raw = out[:idx]
    if status >= 400:
        print(f"HTTP {status}: {raw}", file=sys.stderr)
        sys.exit(1)
    return json.loads(raw) if raw.strip() else {}


def money(v):
    return f"{v/100:,.2f}".replace(",", " ")


def cmd_expenseitems():
    d = req("GET", "/entity/expenseitem", {"limit": 100})
    for x in d["rows"]:
        print(f'{x["id"]}  {x["name"]}')


def cmd_accounts():
    d = req("GET", f"/entity/organization/{ORG_IP}/accounts")
    for x in d["rows"]:
        dflt = " (default)" if x.get("isDefault") else ""
        print(f'{x["id"]}  {x.get("accountNumber","?")!r}  {x.get("bankName","")!r}{dflt}')


def cmd_cp_search():
    q = sys.argv[2]
    params = {"limit": 20, "search": q}
    d = req("GET", "/entity/counterparty", params)
    for x in d["rows"]:
        print(f'{x["id"]}  {x["name"]}  inn={x.get("inn","")}  {x.get("companyType","")}')


def cmd_cp_by_inn():
    inn = sys.argv[2]
    d = req("GET", "/entity/counterparty", {"limit": 20, "filter": f"inn={inn}"})
    for x in d["rows"]:
        print(f'{x["id"]}  {x["name"]}  inn={x.get("inn","")}  {x.get("companyType","")}')
    if not d["rows"]:
        print("(не найдено)")


def cmd_po_list():
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 15
    d = req("GET", "/entity/paymentout", {
        "limit": n, "order": "moment,desc",
        "expand": "expenseItem,agent",
    })
    for x in d["rows"]:
        ei = (x.get("expenseItem") or {}).get("name", "—")
        ag = (x.get("agent") or {}).get("name", "—")
        print(f'{x["moment"][:10]}  №{x["name"]:<7}  {money(x["sum"]):>14}  '
              f'[{ei}]  <{ag}>  :: {x.get("description","")[:60]}')


def cmd_po_get():
    pid = sys.argv[2]
    x = req("GET", f"/entity/paymentout/{pid}",
            {"expand": "expenseItem,agent,organization,organizationAccount,agentAccount"})
    print(json.dumps({
        "id": x["id"], "name": x["name"], "moment": x["moment"],
        "sum": money(x["sum"]), "description": x.get("description"),
        "paymentPurpose": x.get("paymentPurpose"),
        "expenseItem": (x.get("expenseItem") or {}).get("name"),
        "agent": (x.get("agent") or {}).get("name"),
        "agentAccount": (x.get("agentAccount") or {}).get("accountNumber"),
        "organization": (x.get("organization") or {}).get("name"),
        "organizationAccount": (x.get("organizationAccount") or {}).get("accountNumber"),
    }, ensure_ascii=False, indent=2))


def cmd_raw():
    """ms.py raw GET /entity/... key=val key=val"""
    method = sys.argv[2]
    path = sys.argv[3]
    params = dict(a.split("=", 1) for a in sys.argv[4:])
    print(json.dumps(req(method, path, params or None), ensure_ascii=False, indent=2))


META_PATH = {
    "counterparty": "/entity/counterparty/{}",
    "employee": "/entity/employee/{}",
    "expenseitem": "/entity/expenseitem/{}",
}
ORG_META = {"meta": {"href": BASE + f"/entity/organization/{ORG_IP}",
                     "type": "organization", "mediaType": "application/json"}}
ACC_META = {"meta": {"href": BASE + f"/entity/organization/{ORG_IP}/accounts/{ORG_ACC_DEFAULT}",
                     "type": "account", "mediaType": "application/json"}}


def _meta(kind, _id):
    return {"meta": {"href": BASE + META_PATH[kind].format(_id),
                     "type": kind, "mediaType": "application/json"}}


def cmd_mkcp():
    """ms.py mkcp "Имя" [legal|individual]"""
    name = sys.argv[2]
    ctype = sys.argv[3] if len(sys.argv) > 3 else "individual"
    d = req("POST", "/entity/counterparty", body={"name": name, "companyType": ctype})
    print(d["id"], "|", d["name"])


def cmd_post():
    """ms.py post <ops.json> [--dry] [--ledger <name>.jsonl]
    ops.json: [{row, agent_type, agent_id, expense_id, sum_kop, moment, description, account_id?}]
    Идемпотентность через ledger (по умолчанию posted_davydov.jsonl; строка row повторно не проводится).
    """
    ops = json.load(open(sys.argv[2], encoding="utf-8"))
    dry = "--dry" in sys.argv
    ledger_name = "posted_davydov.jsonl"
    if "--ledger" in sys.argv:
        ledger_name = sys.argv[sys.argv.index("--ledger") + 1]
    ledger = os.path.join(os.path.dirname(os.path.abspath(sys.argv[2])), ledger_name)
    done = set()
    if os.path.exists(ledger):
        for ln in open(ledger, encoding="utf-8"):
            if ln.strip():
                done.add(json.loads(ln)["row"])
    for op in ops:
        if op["row"] in done:
            print(f'#{op["row"]}: уже проведён, пропуск')
            continue
        if "account_id" in op:
            acc_meta = {"meta": {"href": BASE + f"/entity/organization/{ORG_IP}/accounts/{op['account_id']}",
                                 "type": "account", "mediaType": "application/json"}}
        else:
            acc_meta = ACC_META
        body = {
            "organization": ORG_META,
            "organizationAccount": acc_meta,
            "agent": _meta(op["agent_type"], op["agent_id"]),
            "expenseItem": _meta("expenseitem", op["expense_id"]),
            "sum": op["sum_kop"],
            "moment": op["moment"],
            "description": op["description"],
        }
        if dry:
            print(f'#{op["row"]} DRY:', json.dumps(body, ensure_ascii=False))
            continue
        d = req("POST", "/entity/paymentout", body=body)
        rec = {"row": op["row"], "id": d["id"], "name": d.get("name"),
               "sum": d["sum"], "moment": d["moment"],
               "url": f'https://online.moysklad.ru/app/#paymentout/edit?id={d["id"]}'}
        with open(ledger, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f'#{op["row"]}: создан №{d.get("name")}  {d["sum"]/100:,.2f}  {rec["url"]}')


def cmd_po_set_sum():
    """ms.py po-set-sum <doc_id> <sum_kop> [description]"""
    doc_id, sum_kop = sys.argv[2], int(sys.argv[3])
    body = {"sum": sum_kop}
    if len(sys.argv) > 4:
        body["description"] = sys.argv[4]
    d = req("PUT", f"/entity/paymentout/{doc_id}", body=body)
    print(f'№{d.get("name")}: sum -> {money(d["sum"])}  desc={d.get("description")!r}')


def cmd_po_delete():
    """ms.py po-delete <doc_id>"""
    doc_id = sys.argv[2]
    req("DELETE", f"/entity/paymentout/{doc_id}")
    print(f"удалён: {doc_id}")


def cmd_po_set_agent():
    """ms.py po-set-agent <doc_id> <counterparty|employee> <agent_id>"""
    doc_id, kind, aid = sys.argv[2], sys.argv[3], sys.argv[4]
    d = req("PUT", f"/entity/paymentout/{doc_id}", body={"agent": _meta(kind, aid)})
    a = req("GET", f"/entity/paymentout/{doc_id}", {"expand": "agent"}).get("agent", {})
    print(f'№{d.get("name")}: agent -> {a.get("name")}')


CMDS = {
    "expenseitems": cmd_expenseitems,
    "accounts": cmd_accounts,
    "cp": cmd_cp_search,
    "cp-inn": cmd_cp_by_inn,
    "po": cmd_po_list,
    "po-get": cmd_po_get,
    "raw": cmd_raw,
    "mkcp": cmd_mkcp,
    "post": cmd_post,
    "po-set-agent": cmd_po_set_agent,
    "po-set-sum": cmd_po_set_sum,
    "po-delete": cmd_po_delete,
}

if __name__ == "__main__":
    if not TOKEN:
        sys.exit("MS_TOKEN не задан")
    if len(sys.argv) < 2 or sys.argv[1] not in CMDS:
        sys.exit("usage: ms.py [" + " | ".join(CMDS) + "]")
    CMDS[sys.argv[1]]()
