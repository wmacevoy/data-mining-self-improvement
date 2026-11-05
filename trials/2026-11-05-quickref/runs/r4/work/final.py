import sys;sys.path.insert(0,"/tmp/pk-r4/work")
import model,prep,pandas as pd,numpy as np
d=pd.read_pickle('d.pkl');h=model.dataset(prep.D+'holdout/status_2026Q3.csv')
print(len(h),h.y.mean(),h.date.min(),h.date.max())
m=model.fit(d);p=model.pred(m,d,h);model.report(h,p,'HOLDOUT GBM')
_,sr=model.addrate(d,h);model.report(h,sr*(h.dow<5),'HOLDOUT station-rate')
model.report(h,(h.b6<=3).astype(float)*.9,'HOLDOUT rule b6<=3')
h=h.assign(p=p);print(h.groupby(pd.cut(h.p,[0,.1,.2,.3,.45,.6,.8,1])).y.agg(['mean','size']))
for k in (4,8,12):print('k',k,model.policy(h,p,k=k))
for thr in (.3,.444,.6):print('thr',thr,model.policy(h,p,thr=thr))
# sanity: shuffled-label model must be ~0.5
from sklearn.metrics import roc_auc_score
r=d.sample(frac=1,random_state=1).y.values;d2=d.assign(y=r);m2=model.fit(d2);print('shuffled AUC',roc_auc_score(h.y,model.pred(m2,d2,h)))
# by month / station
print(h.groupby(h.date.dt.month).apply(lambda g:pd.Series(dict(rate=g.y.mean(),auc=roc_auc_score(g.y,g.p)))))
# daily-features leak check
f=pd.read_csv(prep.D+'daily_features.csv',parse_dates=['date']);x=d.merge(f,on=['station_id','date']);print('daily_features min_bikes_today AUC vs y:',roc_auc_score(x.y,-x.min_bikes_today))
