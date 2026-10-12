import json, sys
for r in json.load(open(sys.argv[1], encoding="utf-8")):
    print(r["row"], r["type"][0], r["date_auth"] or "—", r["date_provod"], f'{r["amount"]:>11,.2f}',
          (r["opis"] or "")[:62], "|", (r["recv_name"] or "")[:28])
