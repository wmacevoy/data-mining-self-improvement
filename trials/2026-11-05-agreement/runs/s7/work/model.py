import pandas as pd, numpy as np, json
from sklearn.ensemble import HistGradientBoostingClassifier as H
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss
p=pd.read_pickle('feat.pkl')
print('y missing by cause: b7 nan',p[p.y.isna()].b7.isna().mean(), 'b8/b9 nan',p[p.y.isna()][['b8','b9']].isna().mean().to_dict())
print('b7==0 prevalence',(p.b7==0).mean(),'y|b7==0',p[p.b7==0].y.mean())
d=p[p.y.notna()].copy()
F=['b7','b6','b5','b7_frac','d67','d56','night_min','capacity','temp_c','rain_mm','dow','prior_rate','prior_rate28','y_prev']
F2=[f for f in F if f not in('b7','b7_frac','d67')]  # variant: no 7:00 reading
d['sid']=d.station_id.str[1:].astype(int); F.append('sid'); F2.append('sid')
def top8(day,score):
    t=day.assign(s=score).nlargest(8,'s'); return t.y.sum()*50-(1-t.y).sum()*40, t.y.sum(), day.y.sum()
def evalfold(tr,te,feats):
    m=H(max_iter=200,learning_rate=0.05,max_depth=4,random_state=0,categorical_features=[feats.index('sid')]).fit(tr[feats],tr.y)
    return m.predict_proba(te[feats])[:,1]
folds=[('2025-10-01','2026-01-01'),('2026-01-01','2026-04-01'),('2026-04-01','2026-07-01')]
rows=[];allp=[]
for a,b in folds:
    tr=d[d.date<a]; te=d[(d.date>=a)&(d.date<b)].copy()
    te['model']=evalfold(tr,te,F)
    te['nob7']=evalfold(tr,te,F2)
    te['persist']=1-te.b7.fillna(te.capacity/2).clip(0,6)/6   # low bikes at 7 -> high score
    te['rate']=te.prior_rate.fillna(0.26)
    allp.append(te)
t=pd.concat(allp)
for c in ['model','nob7','persist','rate']:
    sav=[];tp=[]
    for dt,day in t.groupby('date'):
        r=top8(day,day[c].values); sav.append(r[0]); tp.append((r[1],r[2]))
    tp=np.array(tp)
    # per-fold auc
    aucs=[roc_auc_score(x.y,x[c]) for x in allp]
    print(c,'AUC',np.round(aucs,3),'AP',round(average_precision_score(t.y,t[c]),3),'net$/day',round(np.mean(sav),1),
      '95%CI(day boot)',np.round(np.percentile([np.mean(np.random.default_rng(i).choice(sav,len(sav))) for i in range(500)],[2.5,97.5]),1),
      'caught',tp[:,0].sum(),'of',tp[:,1].sum(),'precision@8',round(tp[:,0].sum()/(8*len(tp)),3))
print('prev',t.y.mean(),'days',t.date.nunique(),'stations/day',len(t)/t.date.nunique(),'stockouts/day',t.y.sum()/t.date.nunique())
print('no-action cost/day',90*t.y.sum()/t.date.nunique(), ' oracle top8 net/day', np.mean([min(day.y.sum(),8)*50 for _,day in t.groupby('date')]))
print('Brier model',brier_score_loss(t.y,t.model),'base',brier_score_loss(t.y,np.full(len(t),d.y.mean())))
# calibration
t['bin']=pd.cut(t.model,[0,.1,.2,.4,.6,.8,1.0],include_lowest=True)
print(t.groupby('bin',observed=True).y.agg(['mean','size']).round(3))
for i,(a,b) in enumerate(folds): 
    x=allp[i]; print(a,'net/day model',round(np.mean([top8(g,g.model.values)[0] for _,g in x.groupby('date')]),1),'persist',round(np.mean([top8(g,g.persist.values)[0] for _,g in x.groupby('date')]),1))
# by station slice
t['pred8']=0
print(t.groupby('station_id').apply(lambda x: pd.Series({'n':len(x),'prev':x.y.mean(),'auc':roc_auc_score(x.y,x.model) if x.y.nunique()>1 else np.nan})).sort_values('auc').head(5).round(2))
print('--- subset b7>0 (not already empty at 7)')
s=t[t.b7>0]
print('n',len(s),'prev',s.y.mean(),'per day',s.y.sum()/t.date.nunique())
for c in ['model','nob7','persist','rate']:
    print(c,'AUC',round(roc_auc_score(s.y,s[c]),3),'AP',round(average_precision_score(s.y,s[c]),3))
for a,b in folds:
    x=t[(t.date>=a)&(t.date<b)]; z=x[x.b7>0]
    print(a,'prev already-empty',round((x.b7==0).mean(),3),'prev new',round(z.y.mean(),3),'AUC new',round(roc_auc_score(z.y,z.model),3))
# new-only decision: crew can only help stations whose 7am reading >0? (empty ones also need bikes) keep both; show share of top8 that are already-empty
tp=[g.nlargest(8,'model') for _,g in t.groupby('date')]
tp=pd.concat(tp); print('share of top8 already empty at 7',(tp.b7==0).mean(),'  days with >8 predicted p>.444',np.mean([ (g.model>0.444).sum()>8 for _,g in t.groupby('date')]))
