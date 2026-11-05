from model import *
f=prep(pd.read_pickle('train.pkl')); a='2026-01-01'
tr=f[f.date<a]; te=f[f.date>=a]
sets={'all':FE,'no_overnight_levels':['cap','y_l1','y_l7m','y_l28m','dow','month','sid'],'no_history':[x for x in FE if not x.startswith('y_')],'last_only':['last','cap','frac','dow','month','sid'],'no_b6':[x for x in FE if x not in('b6','last','frac')]}
for k,v in sets.items():
    m=fit(tr,feats=v);p=m.predict_proba(te[v])[:,1];print(k,round(roc_auc_score(te.y,p),3),round(value(te,p),1))
# local-hour profile by DST period (check clock conversion)
from prep import *
s=load(D+'status.csv');s=s[s.status=='OK']
for nm,m in [('winter',s['loc'].dt.month.isin([12,1,2])),('summer',s['loc'].dt.month.isin([6,7,8]))]:
    print(nm,s[m].groupby('h').bikes_available.mean().round(1).values)
