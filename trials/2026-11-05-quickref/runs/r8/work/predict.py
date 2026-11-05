"""Usage: PYTHONPATH=. python predict.py YYYY-MM-DD   (status/weather files in data/ must run through 06:00 local that day)
Prints stations to restock: top 8 by P(stockout 7-9am) with P > 40/90."""
import sys, pandas as pd
from model import *
import build as B
day=pd.Timestamp(sys.argv[1]); d0=B.build()
d0=d0[d0.dow<5]; T=d0[(d0.date<day)&d0.valid]
m=fit(T,FN); X=d0[d0.date==day]
if X.empty: sys.exit('no rows for that date: status not loaded through 06:00 local')
X=X.assign(p=m.predict_proba(X[FN])[:,1])
print(X[X.p>40/90].nlargest(8,'p')[['station_id','b6','cap','p']].to_string(index=False))
