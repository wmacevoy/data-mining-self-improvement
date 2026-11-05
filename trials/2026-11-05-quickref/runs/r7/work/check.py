import pandas as pd, numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
D='/tmp/pk-r7/data/'
s=pd.read_csv(D+'status.csv',parse_dates=['ts']).drop_duplicates(['ts','station_id'],keep='last')
dst=s.ts.dt.month.isin(range(4,11)) # approx; boundary weeks off by <=1 wk, noted
s['loc']=s.ts+pd.to_timedelta(dst.astype(int),unit='h')  # hypothesis A local clock
s['date']=s['loc'].dt.normalize();s['h']=s['loc'].dt.hour
ok=s.status=='OK'
win=s[s.h.between(7,9)&ok].groupby(['station_id','date']).bikes_available.min().rename('minwin')
pre=s[s.h==6].set_index(['station_id','date'])[['bikes_available','status']].rename(columns={'bikes_available':'b6','status':'st6'})
prev=s[(s.h==5)].set_index(['station_id','date']).bikes_available.rename('b5')
df=pd.concat([win,pre,prev],axis=1).dropna(subset=['minwin']).reset_index()
df['b6']=df.b6.fillna(-1);df['off6']=(df.st6=='OFFLINE').astype(int);df['b5']=df.b5.fillna(-1)
df['y']=(df.minwin==0).astype(int);df['y2']=(df.minwin<=2).astype(int)
print(len(df),df.y.sum(),df.y2.sum())
tr=df[df.date<'2026-01-01'];te=df[df.date>='2026-01-01']
print('dev train/test positives(y2):',tr.y2.sum(),te.y2.sum())
X=['b6','b5','off6'];m=LogisticRegression(max_iter=500).fit(tr[X],tr.y2)
p=m.predict_proba(te[X])[:,1];print('AUC y2',roc_auc_score(te.y2,p),'max p',p.max())
print(df[df.y2==1].groupby('b6').size().to_dict())
