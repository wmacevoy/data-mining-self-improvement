import sys, json, pandas as pd, numpy as np
sys.path.insert(0,'/tmp/pk-s6/work'); import prep
from sklearn.ensemble import HistGradientBoostingClassifier as H
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss
LEDGER='/tmp/pk-s6/work/ledger.jsonl'
def log(**k): open(LEDGER,'a').write(json.dumps(k,default=str)+'\n')
FEATS=['b0','b3','b5','b6','fill6','off6','capacity','dow','temp6','rain6h','prev_y','rate28','b6_mean28']
def policy_cost(df,p,thr=40/90,cap=8):
    """Per day: restock stations with p>thr, at most 8 highest. Assumes a restock prevents the stockout (K4)."""
    df=df.assign(p=p); tot=0; trucks=0; saved=0
    for _,g in df.groupby('date'):
        pick=g[g.p>thr].nlargest(cap,'p'); trucks+=len(pick); saved+=pick.y.sum()
    base=90*df.y.sum()
    return dict(cost=40*trucks+base-90*saved, no_action=base, trucks=trucks, caught=int(saved), stockouts=int(df.y.sum()), days=df.date.nunique())
def evaluate(name,df,p):
    r=dict(name=name,auc=roc_auc_score(df.y,p),brier=brier_score_loss(df.y,np.clip(p,0,1)),**policy_cost(df,p))
    log(split='val',**r); return r
if __name__=='__main__':
    d=pd.read_pickle('/tmp/pk-s6/work/dev.pkl')
    tr=d[d.date<'2026-01-01']; va=d[(d.date>='2026-01-01')]
    out=[]
    # baselines
    out.append(evaluate('yesterday_stockout',va,va.prev_y.fillna(0).values))
    out.append(evaluate('rate28',va,va.rate28.fillna(tr.y.mean()).values))
    out.append(evaluate('zero_bikes_at_6am',va,(va.b6==0).astype(float).values))
    for fs_name,fs in [('all',FEATS),('no_weather_hist',[f for f in FEATS if f not in('temp6','rain6h')]),('no_hist',['b0','b3','b5','b6','fill6','off6','capacity','dow','temp6','rain6h'])]:
        for seed in range(3):
            m=H(max_iter=150,learning_rate=0.05,max_depth=4,random_state=seed).fit(tr[fs],tr.y)
            out.append(evaluate(f'hgb_{fs_name}_s{seed}',va,m.predict_proba(va[fs])[:,1]))
    print(pd.DataFrame(out).round(3).to_string())
