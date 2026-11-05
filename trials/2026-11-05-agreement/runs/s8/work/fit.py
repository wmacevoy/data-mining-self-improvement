"""Time-split evaluation on pre-holdout data. python -I fit.py train_all.csv"""
import sys, pandas as pd, numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier as H
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss
df = pd.read_csv(sys.argv[1], parse_dates=['date']).dropna(subset=['y'])
F = ['capacity','b0_f','b3_f','b5_f','b6_f','b6','prev_min_day','prev_b18','yprev','rate28','rate_all','dow','month','temp6','rain_to6','rain_prev_day']
df['dist']=df.district.astype('category').cat.codes; F.append('dist')
tr = df[df.date<'2026-01-01']; va = df[df.date>='2026-01-01']
print(len(tr),len(va), tr.y.mean(), va.y.mean())
def value(d, p, k=8):
    """per day: restock top-k by p. Value=90*stockouts caught - 40*stops (assumes restock prevents the stockout)."""
    r=[]
    for _,g in d.assign(p=p).groupby('date'):
        t=g.nlargest(k,'p'); r.append((t.y.sum(), k, g.y.sum()))
    r=np.array(r); return r[:,0].mean(), 90*r[:,0].mean()-40*k, r[:,2].mean()
res={}
res['hgb']=np.mean([H(max_iter=200,learning_rate=0.05,max_depth=4,random_state=s).fit(tr[F],tr.y).predict_proba(va[F])[:,1] for s in range(5)],axis=0)
res['rate28']=va.rate28.fillna(tr.y.mean()).values
res['b6_low']=(1-va.b6_f.fillna(.5)).values
res['yprev']=va.yprev.fillna(0).values+0.01*va.rate_all.fillna(0).values
res['random']=np.random.default_rng(0).random(len(va))
for k,p in res.items():
    print(f'{k:8s} auc={roc_auc_score(va.y,p):.3f}', 'caught/day=%.2f net/day=$%.0f stockouts/day=%.2f'%value(va,p))
print('brier hgb',brier_score_loss(va.y,res['hgb']),'base',brier_score_loss(va.y,np.full(len(va),tr.y.mean())))
# crew only goes if p>0.44 (40/90): 
p=res['hgb']; 
for k in (0,4,8,12):
    print('k',k, value(va,p,k) if k else '')
# threshold policy
for th in (.3,.44,.6):
    m=p>th; print('th',th,'stops/day',m.sum()/va.date.nunique(),'precision',va.y[m].mean())
# calibration by decile
va=va.assign(p=p); print(va.groupby(pd.qcut(va.p,10,duplicates='drop'),observed=True).agg(p=('p','mean'),y=('y','mean'),n=('y','size')).round(2))
# per-day bootstrap CI of net at k=8
days=[g for _,g in va.groupby('date')]; rng=np.random.default_rng(1)
nets=np.array([90*g.assign(p=p[va.index.get_indexer(g.index)]).nlargest(8,'p').y.sum()-320 for g in days])
bs=[rng.choice(nets,len(nets)).mean() for _ in range(2000)]; print('net/day k=8 CI',np.percentile(bs,[2.5,97.5]))
# slices
print(va.groupby('district').apply(lambda g: pd.Series({'n':len(g),'rate':g.y.mean(),'auc':roc_auc_score(g.y,g.p)})))
# overall importance-free check: feature drop
