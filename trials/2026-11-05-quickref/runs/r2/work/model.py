import pandas as pd, numpy as np, json, sys
from sklearn.ensemble import HistGradientBoostingClassifier as H
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss
FEATS=['b6','b_last','age_last','b0','b3','b_min_night','b6_minus_b0','cap','frac6','frac_last','off_night','dow','wk','month','temp6','rain_night','y_rate28']
COST_STOP,COST_OUT=40,90; THR=COST_STOP/COST_OUT
def ledger(**k):
    open('LEDGER.jsonl','a').write(json.dumps(k,default=str)+'\n')
def fit(tr,seed=0,**kw):
    m=H(max_iter=200,learning_rate=0.05,max_depth=4,min_samples_leaf=50,random_state=seed,**kw); m.fit(tr[FEATS],tr.y); return m
def cost(df,p,thr=THR,cap=8):
    """per day: restock the top<=8 stations with p>thr (assumes a restock fully prevents the stockout)."""
    tot=0;base=0;n=0
    for d,g in df.assign(p=p).groupby('date'):
        g=g.sort_values('p',ascending=False); pick=g.head(cap); pick=pick[pick.p>thr]
        tot+=COST_STOP*len(pick)+COST_OUT*(g.y.sum()-pick.y.sum()); base+=COST_OUT*g.y.sum(); n+=1
    return tot/n,base/n
def report(name,df,p):
    ok=df.y.notna(); d=df[ok]; pp=np.asarray(p)[ok.values]
    c,b=cost(d,pp)
    r=dict(name=name,n=len(d),rate=d.y.mean(),auc=roc_auc_score(d.y,pp),brier=brier_score_loss(d.y,np.clip(pp,0,1)),cost_day=c,cost_nothing_day=b)
    return r
if __name__=='__main__':
    a=pd.read_pickle('dev.pkl'); a=a[a.y.notna()]
    tr=a[a.date<'2026-01-01']; va=a[a.date>='2026-01-01']
    # baselines
    res=[]
    res.append(report('persist: b_last<=3',va,(va.b_last.fillna(99)<=3).astype(float)))
    res.append(report('station_28d_rate',va,va.y_rate28.fillna(tr.y.mean())))
    res.append(report('const_train_rate',va,np.full(len(va),tr.y.mean())))
    for s in range(5):
        m=fit(tr,s); res.append(report(f'HGB seed{s}',va,m.predict_proba(va[FEATS])[:,1]))
    r=pd.DataFrame(res); print(r.to_string())
    for x in res: ledger(split='train<=2025 val2026H1',**x)
    m=fit(tr,0); va=va.assign(p=m.predict_proba(va[FEATS])[:,1])
    print(va.groupby(pd.cut(va.p,[0,.1,.2,.3,.444,.6,.8,1])).y.agg(['mean','count']))
    imp=None
