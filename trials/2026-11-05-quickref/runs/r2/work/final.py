import pandas as pd,numpy as np,sys
sys.path.insert(0,'/tmp/pk-r2/work')
from model import *
from sklearn.metrics import roc_auc_score
st=pd.read_csv('/tmp/pk-r2/data/stations.csv').drop_duplicates('station_id').set_index('station_id').district
a=pd.read_pickle('dev.pkl'); a=a[a.y.notna()]
tr=a[a.date<'2026-01-01']; va=a[a.date>='2026-01-01'].copy()
m=fit(tr); va['p']=m.predict_proba(va[FEATS])[:,1]; va['d']=va.station_id.map(st)
print('VALIDATION slices')
for k,g in va.groupby('d'): print(k,len(g),round(g.y.mean(),3),'auc',round(roc_auc_score(g.y,g.p),3),'meanp',round(g.p.mean(),3))
for k,g in va.groupby(va.b_last.isna()): print('b_last missing' if k else 'b_last seen',len(g),round(roc_auc_score(g.y,g.p),3),round(g.y.mean(),3),round(g.p.mean(),3))
for k,g in va.groupby(va.date.dt.month): print('month',k,len(g),round(g.y.mean(),3),round(g.p.mean(),3))
# bootstrap by day for cost savings
rng=np.random.default_rng(0); days=va.date.unique(); sv=[]
by={d:g for d,g in va.groupby('date')}
def day_save(g):
    pick=g.sort_values('p',ascending=False).head(8); pick=pick[pick.p>THR]
    return COST_OUT*g.y.sum()-(COST_STOP*len(pick)+COST_OUT*(g.y.sum()-pick.y.sum()))
ds=np.array([day_save(by[d]) for d in days])
bs=[ds[rng.integers(0,len(ds),len(ds))].mean() for _ in range(2000)]
print('VAL saving/day',ds.mean().round(1),np.percentile(bs,[2.5,97.5]).round(1),'ndays',len(ds))
# threshold sweep (looked at on validation: counted)
for t in (.3,.444,.6): print('thr',t,np.mean([ (lambda g:(lambda pk:COST_OUT*g.y.sum()-(COST_STOP*len(pk)+COST_OUT*(g.y.sum()-pk.y.sum())))(g.sort_values('p',ascending=False).head(8).query('p>@t')))(by[d]) for d in days]).round(1))
ledger(note='val slices+bootstrap+thr sweep(3 thresholds)')
# ---- ONE look at holdout
full=fit(a); h=pd.read_pickle('hold_features.pkl')
# y_rate28 for first holdout days uses dev history? holdout built separately: recompute not needed (NaN handled)
hl=h[h.y.notna()].copy(); hl['p']=full.predict_proba(hl[FEATS])[:,1]; hl['d']=hl.station_id.map(st)
r=report('HGB final, holdout 2026Q3 (look #1)',hl,hl.p.values); print(r); ledger(split='HOLDOUT 2026Q3 first and only look',**r)
res=[report('persist b_last<=3',hl,(hl.b_last.fillna(99)<=3).astype(float))]
res.append(report('const dev rate',hl,np.full(len(hl),a.y.mean())))
print(pd.DataFrame(res).to_string()); [ledger(split='HOLDOUT',**x) for x in res]
for k,g in hl.groupby('d'): print(k,len(g),round(g.y.mean(),3),'auc',round(roc_auc_score(g.y,g.p),3),'meanp',round(g.p.mean(),3))
for k,g in hl.groupby(hl.date.dt.month): print('month',k,len(g),round(g.y.mean(),3),round(g.p.mean(),3),'auc',round(roc_auc_score(g.y,g.p),3))
print(hl.groupby(pd.cut(hl.p,[0,.1,.2,.3,.444,.6,.8,1])).y.agg(['mean','count']))
bh={d:g for d,g in hl.groupby('date')}; dh=np.array([day_save(g) for g in bh.values()])
b=[dh[rng.integers(0,len(dh),len(dh))].mean() for _ in range(2000)]
print('HOLDOUT saving/day',dh.mean().round(1),np.percentile(b,[2.5,97.5]).round(1),len(dh))
hl.to_pickle('hold_scored.pkl')
