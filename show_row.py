import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
want = {int(x) for x in sys.argv[2:]}
for r in d:
    if r["row"] in want:
        print(r["row"], r["type"], r["amount"], r["date_auth"], "|", r["opis"], "| recv=", r["recv_name"], r["recv_inn"], "| payer=", r["payer_name"])
