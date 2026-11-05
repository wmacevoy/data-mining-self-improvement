import pandas as pd,numpy as np,sys
sys.path.insert(0,'/tmp/pk-r2/work')
from sklearn.metrics import roc_auc_score as A
import prep
s=prep.load('/tmp/pk-r2/data/status.csv')
w=s[s.h.isin([7,8,9])].groupby(['station_id','date']).apply(lambda d:pd.Series({'y':float((d.ok&(d.bikes_available==0)).any()),'c':float(len(d)==3 and d.ok.all())}))
w=w[w.c==1]
p=s.pivot_table(index=['station_id','date'],columns='h',values='bikes_available',aggfunc='last')
d=p.join(w.y,how='inner')
for h in (1,3,4,5,6,7,8):
    x=d[d[h].notna()]; print('hour',h,'AUC(-bikes)',round(A(x.y,-x[h]),3))
