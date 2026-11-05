"""One-shot sign-off on holdout. Model hyperparameters were fixed before this look (no tuning done on validation either)."""
import pandas as pd, numpy as np
from sklearn.metrics import roc_auc_score, brier_score_loss
import sys; sys.path.insert(0,"/tmp/pk-r6/work")
import build, model
D=build.D
full=build.build([D+'status.csv',D+'holdout/status_2026Q3.csv'])
full.to_pickle('full.pkl')
d=model.wk(full)
tr=d[d.date<'2026-07-01']; ho=d[d.date>='2026-07-01']
# tune the simple rule on train only
best=min(range(0,9),key=lambda k:model.cost(tr,(tr.b6.fillna(0)<=k).astype(float).values,thr=.4)['cost'])
print('rule k',best)
m=model.fit(tr); p=m.predict_proba(ho[model.F])[:,1]
y=ho.stockout
print(len(ho),ho.date.min(),ho.date.max(),'base rate',y.mean(), 'unknown-label rows dropped',((full.dow<5)&(full.lab_known==0)&(full.date>='2026-07-01')).sum())
print('AUC',roc_auc_score(y,p),'Brier',brier_score_loss(y,p),'Brier const',brier_score_loss(y,np.full(len(y),tr.stockout.mean())))
# bootstrap by day
rng=np.random.default_rng(0); days=ho.date.unique(); res=[]
ho=ho.assign(p=p)
for _ in range(200):
    ds=rng.choice(days,len(days)); b=pd.concat([ho[ho.date==x] for x in ds]) if False else None
rule=(ho.b6.fillna(0)<=best).astype(float).values
for n,q,t in [('model',p,40/90),('rule',rule,.4),('rate28',ho.rate28.fillna(0).values,.4)]:
    print(n,model.cost(ho,q,thr=t))
# per-day savings bootstrap
def perday(q,t):
    out=[]
    for dt,g in ho.assign(q=q).groupby('date'):
        sel=g[g.q>t].nlargest(8,'q'); out.append(90*g.stockout.sum()-(40*len(sel)+90*g.drop(sel.index).stockout.sum()))
    return np.array(out)
sm,sr=perday(p,40/90),perday(rule,.4)
for n,s in [('model saving/day',sm),('model-rule/day',sm-sr)]:
    bs=[rng.choice(s,len(s)).mean() for _ in range(2000)]; print(n,s.mean().round(1),np.percentile(bs,[2.5,97.5]).round(1))
print(ho.groupby(pd.cut(p,[0,.1,.2,.3,.45,.6,.8,1])).agg(n=('p','size'),pred=('p','mean'),obs=('stockout','mean')).round(3))
print(ho.groupby(ho.station_id>='S025').apply(lambda g:pd.Series(dict(n=len(g),auc=roc_auc_score(g.stockout,g.p),obs=g.stockout.mean(),pred=g.p.mean()))))
print(ho.groupby('month').apply(lambda g:pd.Series(dict(n=len(g),obs=g.stockout.mean(),pred=g.p.mean()))))
