import sys
sys.path.insert(0, r"C:\pb")
import ms

since = sys.argv[1]
d = ms.req("GET", "/entity/paymentout", {
    "limit": 100, "order": "moment,asc",
    "filter": f"moment>={since} 00:00:00",
    "expand": "organizationAccount,agent,expenseItem",
})
print("найдено:", d["meta"]["size"])
for x in d["rows"]:
    acc = (x.get("organizationAccount") or {}).get("accountNumber", "?")
    ag = (x.get("agent") or {}).get("name", "—")
    ei = (x.get("expenseItem") or {}).get("name", "—")
    print(f'{x["moment"][:10]} №{x["name"]} {x["sum"]/100:>12,.2f} [{acc.strip()}] <{ag}> [{ei}] :: {x.get("description","")[:50]}')
