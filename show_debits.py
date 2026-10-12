import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
for r in d:
    if r["type"] == "Дебет":
        print(r["row"], r["date_provod"], f'{r["debit"]:>12,.2f}', r["opis"][:55], "| recv=", r["recv_name"])
