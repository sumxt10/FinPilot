import sys
sys.path.insert(0,".")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
import json, pandas as pd, agents as A
from data.generate_data import make
make(); S=A.run_pipeline(pd.read_csv("data/transactions.csv"),json.load(open("data/profile.json")))
df=S["df"]; acc=(df.category.values==df.true_category.values).mean()
print(f"Categorization accuracy: {acc:.1%}"); print("Anomalies:",[(a['kind'],a['merchant']) for a in S['anomalies']])
print("Health:",S["health"]["score"],"| Forecast:",S["forecast"]["risk"],round(S["forecast"]["min_balance"]),"| Alerts:",len(S["alerts"]),"| Approved:",S["review"]["approved"])
print("Advice:",[(a['title'],a['saving']) for a in S['advice']])
for t in S["trace"]: print(t["agent"],"|",t["summary"])
