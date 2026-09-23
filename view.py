import sys, json
recs = json.load(open(sys.argv[1], encoding="utf-8"))
mode = sys.argv[2] if len(sys.argv) > 2 else "days"

def base_date(r):
    return r["date_auth"] or r["date_provod"]

if mode == "days":
    from collections import defaultdict
    by = defaultdict(lambda: [0, 0.0, 0.0])
    for r in recs:
        k = base_date(r)
        by[k][0] += 1
        by[k][1] += r["debit"]
        by[k][2] += r["credit"]
    for k in sorted(by, key=lambda s: (s.split(".")[::-1])):
        n, dsum, csum = by[k]
        print(f"{k}  ops={n:3}  debit={dsum:>12,.2f}  credit={csum:>12,.2f}")

elif mode == "day":
    day = sys.argv[3]
    sel = [r for r in recs if base_date(r) == day]
    print(f"=== {day} : {len(sel)} операций ===")
    for r in sel:
        tag = "РАСХ" if r["type"] == "Дебет" else "ПРИХ"
        cp = r["cp_name"] or r["recv_name"] or r["payer_name"] or "—"
        extra = f" mcc={r['mcc']}" if r["mcc"] else ""
        print(f'#{r["row"]:3} {tag} {r["amount"]:>11,.2f}  auth={r["date_auth"] or "—"} provod={r["date_provod"]}'
              f'\n      opis: {r["opis"]}'
              f'\n      cp: {cp}  inn={r["cp_inn"] or r["recv_inn"] or "—"}{extra}')

elif mode == "range":
    a, b = sys.argv[3], sys.argv[4]
    def key(s):
        d, m, y = s.split(".")
        return (y, m, d)
    sel = [r for r in recs if a <= "".join(key(base_date(r))) <= b] if False else \
          [r for r in recs if key(a) <= key(base_date(r)) <= key(b)]
    for r in sel:
        tag = "РАСХ" if r["type"] == "Дебет" else "ПРИХ"
        cp = r["cp_name"] or r["recv_name"] or r["payer_name"] or "—"
        print(f'#{r["row"]:3} {base_date(r)} {tag} {r["amount"]:>11,.2f}  {r["opis"][:55]:55}  | {cp[:35]}')
