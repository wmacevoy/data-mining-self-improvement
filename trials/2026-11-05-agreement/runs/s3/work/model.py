"""Validation on 2026-01..06 (train 2025). Appends every scored config to ledger.csv. Holdout never read."""
import pandas as pd, numpy as np, csv, os, sys
from sklearn.ensemble import HistGradientBoostingClassifier as HGB
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss
from build import build
LEDGER='/tmp/pk-s3/work/ledger.csv'
def log(name,split,**m):
    new=not os.path.exists(LEDGER)
    with open(LEDGER,'a',newline='') as f:
        w=csv.writer(f)
        if new:w.writerow(['config','split','metrics'])
        w.writerow([name,split,str(m)])
FEATS=['b7f','b6f','d1','off7','prev_label','prev_min','capacity','fill','dow','month','temp7','rain7','rain24','restocked_prev']
FEATS_S=['b7f','capacity','fill','prev_label','dow','temp7','rain24','restocked_prev','off7']
def station_rate(tr): return tr.groupby('station_id').label.mean()
def decide(df,score,k=8,thr=40/130):
    """Per day: top-k scores above thr. Returns net $ saved vs doing nothing, stops, stockouts caught."""
    out=[]
    for d,g in df.assign(s=score).groupby('date'):
        c=g[g.s>thr].nlargest(k,'s')
        out.append((90*c.label.sum()-40*len(c),len(c),c.label.sum(),g.label.sum()))
    o=np.array(out); return o.mean(0)
def run(tr,va,seed=0):
    res={}
    base_rate=va.station_id.map(station_rate(tr)).fillna(tr.label.mean()).values
    res['stn_rate']=base_rate
    res['low_bikes']=(1-va.fill.fillna(0.5)).values  # persistence: emptiest at 7:00
    X=lambda d,f:d[f].astype(float)
    ps=[]
    for sd in range(5):
        m=HGB(max_iter=200,learning_rate=0.05,max_depth=4,random_state=sd).fit(X(tr,FEATS),tr.label)
        ps.append(m.predict_proba(X(va,FEATS))[:,1])
    res['hgb']=np.mean(ps,0); res['hgb_seeds']=ps
    lr=LogisticRegression(C=1,max_iter=2000)
    med=X(tr,FEATS_S).median()
    lr.fit(X(tr,FEATS_S).fillna(med),tr.label); res['logit']=lr.predict_proba(X(va,FEATS_S).fillna(med))[:,1]
    return res
if __name__=='__main__':
    r=build().dropna(subset=['label'])
    tr=r[r.date<'2026-01-01']; va=r[(r.date>='2026-01-01')]
    res=run(tr,va)
    y=va.label.values
    print('n val',len(va),'rate',y.mean(),'train rate',tr.label.mean())
    for k in ['stn_rate','low_bikes','logit','hgb']:
        s=res[k]; a=roc_auc_score(y,s)
        d=decide(va,s) if k in('hgb','logit','stn_rate') else decide(va,s,thr=0.5)  # low_bikes: fill<0.5 is not a prob
        print(k,'auc %.3f'%a,'$/day %.1f stops %.1f caught %.1f of %.1f'%tuple(d))
        log(k,'train2025_val2026H1',auc=round(a,4),usd_day=round(d[0],1))
    for i,p in enumerate(res['hgb_seeds']): print(' seed',i,round(roc_auc_score(y,p),4),round(decide(va,p)[0],1))
    print('brier hgb',brier_score_loss(y,res['hgb']),'base',brier_score_loss(y,np.full(len(y),tr.label.mean())))
    # oracle & naive
    orc=decide(va,y.astype(float)); print('oracle',orc)
    va=va.assign(p=res['hgb'])
    va['bin']=pd.cut(va.p,[0,.1,.2,.3,.5,.7,.9,1]); print(va.groupby('bin',observed=True).label.agg(['mean','size']))
    print(va.groupby(va.date.dt.month).apply(lambda g:pd.Series({'auc':roc_auc_score(g.label,g.p),'rate':g.label.mean(),'usd':decide(g,g.p.values)[0]})))
    print(va.groupby('district').apply(lambda g:pd.Series({'auc':roc_auc_score(g.label,g.p),'rate':g.label.mean(),'n':len(g)})))
    va.to_pickle('/tmp/pk-s3/work/val_pred.pkl')
