import sys, pandas as pd, numpy as np
sys.path.insert(0,'/tmp/pk-s6/work'); import model as M
from sklearn.ensemble import HistGradientBoostingClassifier as H
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
d=pd.read_pickle('/tmp/pk-s6/work/dev.pkl')
tr=d[d.date<'2026-01-01']; va=d[d.date>='2026-01-01'].reset_index(drop=True)
fs=M.FEATS
hgb=H(max_iter=150,learning_rate=0.05,max_depth=4,random_state=0).fit(tr[fs],tr.y)
p_h=hgb.predict_proba(va[fs])[:,1]
lf=['fill6','b6','capacity']
imp=lambda x:x.fillna(tr[lf].median())
lr=LogisticRegression(max_iter=1000).fit(imp(tr[lf]),tr.y); p_l=lr.predict_proba(imp(va[lf]))[:,1]
# simple rule: restock the 8 emptiest at 6am (always 8 trucks, no threshold)
def rule_cost(df,k=8):
    tot=0;caught=0;tr_=0
    for _,g in df.groupby('date'):
        pick=g.nsmallest(k,'fill6'); pick=pick[pick.fill6.notna()]; tr_+=len(pick); caught+=pick.y.sum()
    return 40*tr_+90*(df.y.sum()-caught)
for k in (0,4,8): M.log(split='val',name=f'rule_lowest_fill_top{k}',cost=rule_cost(va,k) if k else 90*va.y.sum())
print('rule top8 cost',rule_cost(va,8),'top4',rule_cost(va,4),'none',90*va.y.sum())
M.log(split='val',name='logit_fill6_b6_cap',**M.policy_cost(va,p_l)); print('logit',M.policy_cost(va,p_l))
M.log(split='val',name='hgb_all_final',**M.policy_cost(va,p_h)); print('hgb',M.policy_cost(va,p_h))
# bootstrap days
rng=np.random.default_rng(0); days=va.date.unique(); g={k:v for k,v in va.assign(ph=p_h,pl=p_l).groupby('date')}
res=[]
for _ in range(300):
    pick=rng.choice(len(days),len(days)); parts=[g[days[i]] for i in pick]
    # distinct date labels so groupby keeps resampled days separate
    b=pd.concat([x.assign(date=j) for j,x in enumerate(parts)])
    ch=M.policy_cost(b,b.ph.values); cl=M.policy_cost(b,b.pl.values); noact=ch['no_action']
    res.append((noact-ch['cost'],noact-cl['cost'],roc_auc_score(b.y,b.ph)))
r=np.array(res)
for i,n in enumerate(['hgb saving $','logit saving $','hgb AUC']): print(n,np.percentile(r[:,i],[2.5,50,97.5]).round(3))
va['p']=p_h
print('calibration'); print(va.groupby(pd.cut(va.p,[0,.1,.2,.3,.444,.6,.8,1.0]),observed=True).y.agg(['mean','size']))
print('by month'); print(va.groupby(va.date.dt.month).apply(lambda x:pd.Series(dict(n=len(x),rate=x.y.mean(),auc=roc_auc_score(x.y,x.p),**{k:v for k,v in M.policy_cost(x,x.p.values).items() if k in('cost','no_action')}))).round(3))
print('by district'); print(va.groupby('district').apply(lambda x:pd.Series(dict(n=len(x),rate=x.y.mean(),auc=roc_auc_score(x.y,x.p)))).round(3))
print('missing b6 rows',va.b6.isna().sum(), va[va.b6.isna()].y.mean(), 'auc',roc_auc_score(va.y,va.p))
print('trucks/day dist'); print(va[va.p>40/90].groupby('date').size().describe())
import pickle; pickle.dump(hgb,open('/tmp/pk-s6/work/model_trained_to_2025.pkl','wb'))
