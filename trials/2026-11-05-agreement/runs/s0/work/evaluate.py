"""Rolling-origin evaluation on dev data only (status.csv). Appends every config scored to ledger.csv."""
import sys, json, numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier as HGB
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss
FEATS=['frac_h0','frac_h3','frac_h6','min_ovn','capacity','empty_lag1','rate_prev14','rate_prev60','minfrac_prev14','temp6','rain_ovn','rain_prevday','dow','month']
TRUCK,LOSS,CREW=40,90,8
def prep(d):
    d=d[d.n_obs>0].copy(); d['y']=d['empty'].astype(int); d['sid']=d.station_id.str[1:].astype(int); return d
def net(df,p):
    """$ saved per day vs doing nothing: visit up to 8 highest-p stations with p>40/90; a visit prevents that station's stockout (assumption)."""
    tot=0;days=0
    for _,g in df.assign(p=p).groupby('date'):
        v=g[g.p>TRUCK/LOSS].nlargest(CREW,'p'); tot+=(LOSS*v.y-TRUCK).sum(); days+=1
    return tot/days
def oracle(df):
    return net(df,df.y.values.astype(float))
def models():
    return {'hgb':lambda:HGB(max_iter=150,learning_rate=0.05,max_depth=4,min_samples_leaf=40,random_state=0),
            'hgb_nostation':lambda:HGB(max_iter=150,learning_rate=0.05,max_depth=4,min_samples_leaf=40,random_state=0)}
def fit_pred(name,tr,te,seed=0):
    F=FEATS+(['sid'] if name=='hgb' else [])
    m=HGB(max_iter=150,learning_rate=0.05,max_depth=4,min_samples_leaf=40,random_state=seed)
    m.fit(tr[F],tr.y); return m.predict_proba(te[F])[:,1]
def baselines(tr,te):
    out={}
    out['none']=np.zeros(len(te))
    out['yesterday']=te.empty_lag1.fillna(0).values*0.9
    out['station_rate60']=te.rate_prev60.fillna(tr.y.mean()).values
    return out
if __name__=='__main__':
    d=prep(pd.read_csv('dev.csv',parse_dates=['date']))
    folds=[('2025-10-01','2026-01-01'),('2026-01-01','2026-04-01'),('2026-04-01','2026-07-02')]
    rows=[]
    for a,b in folds:
        tr=d[d.date<pd.Timestamp(a)-pd.Timedelta(days=1)]; te=d[(d.date>=a)&(d.date<b)]
        preds=baselines(tr,te)
        for name in ('hgb','hgb_nostation'):
            ps=[fit_pred(name,tr,te,s) for s in range(5)]
            preds[name]=np.mean(ps,0)
            preds[name+'_seed_sd_net']=None
            seednet=[net(te,p) for p in ps]; 
            rows.append(dict(fold=a,model=name+'_seedspread',net_per_day=np.mean(seednet),sd=np.std(seednet),auc=None,brier=None,n=len(te)))
        for k,p in preds.items():
            if p is None: continue
            auc=roc_auc_score(te.y,p) if len(set(p))>1 else np.nan
            rows.append(dict(fold=a,model=k,net_per_day=net(te,p),sd=np.nan,auc=auc,brier=brier_score_loss(te.y,np.clip(p,0,1)),n=len(te)))
        rows.append(dict(fold=a,model='oracle',net_per_day=oracle(te),sd=np.nan,auc=1,brier=0,n=len(te)))
        rows.append(dict(fold=a,model='base_rate',net_per_day=np.nan,sd=np.nan,auc=np.nan,brier=te.y.mean(),n=len(te)))
    r=pd.DataFrame(rows); r.to_csv('ledger.csv',index=False)
    print(r.round(3).to_string())
