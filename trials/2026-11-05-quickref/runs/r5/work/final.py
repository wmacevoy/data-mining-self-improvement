"""Run ONCE. Fit on all data through 2026-06-30; score the 2026Q3 holdout. Holdout is read only here."""
import pandas as pd, numpy as np, json, os
from prep import *; from model import *
from sklearn.metrics import roc_auc_score, average_precision_score
assert not os.path.exists('HOLDOUT_SPENT'), 'holdout already spent'
open('HOLDOUT_SPENT','w').write('spent by final.py\n')
a=pd.read_csv(D+'status.csv');b=pd.read_csv(D+'holdout/status_2026Q3.csv')
print('overlap',len(set(a.ts)&set(b.ts)),b.ts.min(),b.ts.max())
pd.concat([a,b]).drop_duplicates(['ts','station_id'],keep='last').to_csv('/tmp/all_status.csv',index=False)
w=pd.read_csv(D+'weather.csv',parse_dates=['ts_local'])
d=add_feats(build('/tmp/all_status.csv'),w)
u=usable(d);tr=u[u.date<'2026-07-01'];ho=u[u.date>='2026-07-01']
print('holdout rows',len(ho),'of',(d.date>='2026-07-01').sum(),'rate',ho.y.mean(),'days',ho.date.nunique())
m=fit(tr,'hgb');p=m.predict_proba(ho[F])[:,1]
res={}
def cst(sc,thr): return cost(ho,sc,thr)
res['never']=OUT*ho.groupby('date').y.sum().mean()
res['stockouts_per_day']=ho.groupby('date').y.sum().mean()
res['model']=cst(p,0.444);res['model_top8_always']=cst(p,None)
res['persist']=cst(ho.y_prev1.fillna(0).values+1e-3*(1-ho.b6f.values),0.5)
res['rule_b6<=2']=cst((-ho.b6).values,-2.5)
res['auc']=roc_auc_score(ho.y,p);res['ap']=average_precision_score(ho.y,p)
# bootstrap by day of cost saving vs never
rng=np.random.default_rng(0);ho=ho.assign(p=p);days=ho.date.unique();per=[]
for dd,g in ho.groupby('date'):
    pk=g.nlargest(CREW,'p');pk=pk[pk.p>.444];per.append((OUT*g.y.sum(),STOP*len(pk)+OUT*(g.y.sum()-pk.y.sum()),len(pk),pk.y.sum(),g.y.sum()))
per=np.array(per);sv=[ (per[i,0]-per[i,1]).mean() for i in (rng.integers(0,len(per),len(per)) for _ in range(2000))]
res['saving_vs_never_mean']=float((per[:,0]-per[:,1]).mean());res['saving_ci95']=[float(np.percentile(sv,2.5)),float(np.percentile(sv,97.5))]
res['stops_per_day']=float(per[:,2].mean());res['precision']=float(per[:,3].sum()/per[:,2].sum());res['recall']=float(per[:,3].sum()/per[:,4].sum())
ho['bin']=pd.cut(ho.p,[0,.05,.1,.2,.444,.7,1]);print(ho.groupby('bin',observed=True).agg(n=('y','size'),pred=('p','mean'),obs=('y','mean')))
print(ho.groupby('district').apply(lambda g:pd.Series({'n':len(g),'rate':g.y.mean(),'meanp':g.p.mean()}),include_groups=False))
res['n_dev_configs_scored_on_validation']=7
print(json.dumps(res,indent=1,default=float));json.dump(res,open('holdout_result.json','w'),indent=1,default=float)
