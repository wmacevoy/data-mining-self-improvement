import pandas as pd, numpy as np, json, warnings; warnings.filterwarnings('ignore')
from sklearn.ensemble import HistGradientBoostingClassifier as H
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss
df=pd.read_pickle('/tmp/pk-s4/work/rows.pkl'); df=df[df.y.notna()].copy()
df['sid']=df.station_id.str[1:].astype(int)
TR=df[df.date<'2026-03-01']; VA=df[df.date>='2026-03-01']
F=['b6','f6','b5','d6','off_pre','cap','y_prev','rate28','mb6_28','dow','month','t6','rain6']
ledger=[]
def log(name,**k): ledger.append(dict(name=name,**k))
def policy(d,score,k=8,thr=None):
    d=d.assign(s=score); out=[]
    for dt,g in d.groupby('date'):
        top=g.nlargest(k,'s'); top=top[top.s>=thr] if thr is not None else top
        out.append((len(top),top.y.sum(),g.y.sum()))
    a=np.array(out); trucks,hit,tot=a.sum(0)
    return dict(stops=int(trucks),caught=int(hit),stockouts=int(tot),cost=int(40*trucks+90*(tot-hit)),do_nothing=int(90*tot))
res={}
y=VA.y.values
cands={'rate28 (station trailing rate)':VA.rate28.fillna(TR.y.mean()).values,
       'yesterday stockout':VA.y_prev.fillna(0).values,
       'low 6am fill (1-f6)':(1-VA.f6.fillna(0.5)).values}
for n,sc in cands.items(): res[n]=sc
for seed in range(5):
    m=H(max_iter=200,learning_rate=0.05,max_depth=4,min_samples_leaf=40,random_state=seed).fit(TR[F],TR.y)
    res[f'gbm seed{seed}']=m.predict_proba(VA[F])[:,1]
res['gbm mean5']=np.mean([res[f'gbm seed{i}'] for i in range(5)],axis=0)
Fl=['f6','rate28','y_prev','off_pre']
X=lambda d:d[Fl].fillna(d[Fl].median())
lr=LogisticRegression(max_iter=500).fit(X(TR),TR.y); res['logreg']=lr.predict_proba(X(VA))[:,1]
rows=[]
rng=np.random.default_rng(0)
for n,sc in res.items():
    p=policy(VA,sc,8); pt=policy(VA,sc,8,thr=40/90)
    r=dict(model=n,auc=roc_auc_score(y,sc),ap=average_precision_score(y,sc),**{'top8_'+k:v for k,v in p.items()},**{'thr_'+k:v for k,v in pt.items()})
    rows.append(r); log(n,split='train<2026-03, val 2026-03..06',**{k:(float(v) if not isinstance(v,str) else v) for k,v in r.items() if k!='model'})
R=pd.DataFrame(rows).set_index('model'); pd.set_option('display.width',250); print(R.round(3).to_string())
print('val rows',len(VA),'base rate',y.mean(), 'days',VA.date.nunique(),'stockouts/day',y.sum()/VA.date.nunique())
sc=res['gbm mean5']; print('brier',brier_score_loss(y,sc),'const',brier_score_loss(y,np.full(len(y),TR.y.mean())))
# calibration
q=pd.qcut(sc,8,duplicates='drop'); print(VA.assign(p=sc,q=q).groupby('q').agg(p=('p','mean'),y=('y','mean'),n=('y','size')).round(3))
# bootstrap by day: gbm saving vs best baseline
days=VA.date.unique(); VA2=VA.assign(g=sc,r=res['rate28 (station trailing rate)'])
def sav(dd):
    a=policy(dd,dd.g.values,8,40/90); b=policy(dd,dd.r.values,8,None); return a['cost'],b['cost'],a['do_nothing']
bs=[]
for _ in range(200):
    pick=rng.choice(days,len(days)); dd=pd.concat([VA2[VA2.date==d] for d in pick]); a,b,c=sav(dd); bs.append((c-a,c-b))
bs=np.array(bs); print('saving vs nothing gbm  ci',np.percentile(bs[:,0],[5,50,95]),'baseline rate28 top8',np.percentile(bs[:,1],[5,50,95]),'gap',np.percentile(bs[:,0]-bs[:,1],[5,50,95]))
# slices
VA2['pred']=sc
print(VA.assign(p=sc).groupby('month').apply(lambda g:pd.Series(dict(n=len(g),rate=g.y.mean(),auc=roc_auc_score(g.y,g.p)))).round(3))
print(VA.assign(p=sc).merge(pd.read_csv('/tmp/pk-s4/data/stations.csv').drop_duplicates('station_id')[['station_id','district']]).groupby('district').apply(lambda g:pd.Series(dict(n=len(g),rate=g.y.mean(),auc=roc_auc_score(g.y,g.p)))).round(3))
pd.DataFrame(ledger).to_csv('/tmp/pk-s4/work/ledger.csv',index=False)
